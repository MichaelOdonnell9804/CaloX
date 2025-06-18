#!/usr/bin/env python3

import sys
import os
import time

# ensure CMSPLOTS is on the path
sys.path.append("CMSPLOTS")  # noqa

import ROOT
from CMSPLOTS.myFunction import DrawHistos
from utils.html_generator import generate_html
from utils.CaloXChannel import FERSBoard, DRSBoard

# Batch mode for offscreen usage
ROOT.gROOT.SetBatch(True)

# === GLOBAL STYLE SETTINGS ===
# Clean style, no stats box, fixed 3:2 canvas ratio
ROOT.gStyle.SetOptStat(0)
ROOT.gStyle.SetOptTitle(0)
ROOT.gStyle.SetCanvasDefW(400)
ROOT.gStyle.SetCanvasDefH(600)
ROOT.gStyle.SetPadLeftMargin(0.12)
ROOT.gStyle.SetPadRightMargin(0.10)
ROOT.gStyle.SetPadTopMargin(0.08)
ROOT.gStyle.SetPadBottomMargin(0.12)
ROOT.gStyle.SetTitleFont(42, "")
ROOT.gStyle.SetTitleFontSize(0.05)
ROOT.gStyle.SetLabelFont(42, "XY")
ROOT.gStyle.SetLabelSize(0.04, "XY")
ROOT.gStyle.SetTitleOffset(1.2, "Y")

# === USER CONFIGURATION ===
runNumber    = 624
outdir       = f"plots/Run{runNumber}"
HG_THRESHOLD = 8000.0  # only save/plot events where any HG channel > this

# --- tiny utils ---
def number2string(n):
    s = str(n)
    return s.replace('-', 'm').replace('.', 'p')

def string2number(s):
    return float(s.replace('m', '-').replace('p', '.'))

# --- channel-map builders ---
def buildFERSBoards(run=583):
    base_6mm = FERSBoard(boardNo=-1, is6mm=True)
    base_3mm = FERSBoard(boardNo=-1, is6mm=False)

    FERSBoards = {
        f"Board{n}": (base_6mm.copy(boardNo=n) if n not in (6,7)
                      else base_3mm.copy(boardNo=n))
        for n in range(14)
    }

    for ix in range(4):
        for iy in range(16):
            fb = FERSBoards
            fb["Board0"][ ix,iy].iTowerX -= 12; fb["Board0"][ ix,iy].iTowerY += 6
            fb["Board1"][ ix,iy].iTowerX -=  8; fb["Board1"][ ix,iy].iTowerY +=10
            fb["Board2"][ ix,iy].iTowerX -=  4; fb["Board2"][ ix,iy].iTowerY +=10
            fb["Board3"][ ix,iy].iTowerX +=  0; fb["Board3"][ ix,iy].iTowerY +=12
            fb["Board4"][ ix,iy].iTowerX +=  4; fb["Board4"][ ix,iy].iTowerY +=10
            fb["Board5"][ ix,iy].iTowerX +=  8; fb["Board5"][ ix,iy].iTowerY +=10

            fb["Board8"][ ix,iy].iTowerX -=  8; fb["Board8"][ ix,iy].iTowerY += 2
            fb["Board9"][ ix,iy].iTowerX -=  4; fb["Board9"][ ix,iy].iTowerY += 2
            fb["Board10"][ix,iy].iTowerX +=  0; fb["Board10"][ix,iy].iTowerY += 0
            fb["Board11"][ix,iy].iTowerX +=  4; fb["Board11"][ix,iy].iTowerY += 2
            fb["Board12"][ix,iy].iTowerX +=  8; fb["Board12"][ix,iy].iTowerY += 2

            fb["Board13"][ix,iy].iTowerX += 12; fb["Board13"][ix,iy].iTowerY += 6
            fb["Board7"][ ix,iy].iTowerX +=  2; fb["Board7"][ ix,iy].iTowerY += 4.25
            fb["Board6"][ ix,iy].iTowerX +=  0; fb["Board6"][ ix,iy].iTowerY += 4.25

    return FERSBoards


def buildDRSBoards(run=None):
    base = DRSBoard(boardNo=-1)
    DRSBoards = {
        "Board0": base.copy(boardNo=0),
        "Board2": base.copy(boardNo=2),
    }
    for ix in range(4):
        for iy in range(8):
            DRSBoards["Board2"][ix,iy].iTowerY -= 4
    return DRSBoards


def getBoardDrawables(boards):
    drawables = []
    for F in boards.values():
        xs, ys = zip(*F.GetListOfTowers())
        x_min, x_max = min(xs)-0.5, max(xs)+0.5
        y_min, y_max = min(ys)-0.5, max(ys)+0.5

        box = ROOT.TBox(x_min, y_min, x_max, y_max)
        box.SetLineColor(ROOT.kRed)
        box.SetLineWidth(2)
        box.SetFillStyle(0)
        drawables.append(box)
        label = ROOT.TLatex(0.5*(x_min+x_max), 0.5*(y_min+y_max), f"B{F.boardNo}")

        label.SetTextColor(ROOT.kRed)
        label.SetTextAlign(22)
        label.SetTextSize(0.04)
        drawables.append(label)

    return drawables    


def makeEventDisplays(infilename):
    start_time = time.time()
    infile = ROOT.TFile(infilename, "READ")
    if not infile or infile.IsZombie():
        raise RuntimeError(f"Failed to open input file: {infile}")

    tree = infile.Get("EventTree")
    if not tree:
        raise RuntimeError("EventTree not found")
    # only do the first 100 events
    nEvents = tree.GetEntries()
    nEventsToProcess = min(nEvents, 5000)
    print(f"Total events in file: {nEvents}")

    DRSBoards  = buildDRSBoards()
    FERSBoards = buildFERSBoards()

    evdisp_dir = os.path.join(outdir, "event_display")
    pulse_dir  = os.path.join(outdir, "pulse_shapes")
    os.makedirs(evdisp_dir, exist_ok=True)
    os.makedirs(pulse_dir,  exist_ok=True)

    plots_eventdisplay = []
    plots_pulse_shapes = []
    hists_eventdisplay = []
    hists_pulse_shapes = []

    iX_min, iX_max = -12.5, 15.5
    iY_min, iY_max = -7.5, 12.5
    W_ref = 1000

    for ievt in range(nEventsToProcess):

        tree.GetEntry(ievt)
        evtNumber = tree.event_n

        maxHG = 0.0
        for F in FERSBoards.values():
            arr64 = getattr(tree, f"FERS_Board{F.boardNo}_energyHG")
            if len(arr64):
                maxHG = max(maxHG, max(arr64))
        if maxHG < HG_THRESHOLD:
            continue

        print(f"Event {ievt+1}/{nEvents} (evt#{evtNumber}): maxHG={maxHG:.1f}")

        # Create 2D histograms
        h2_Cer     = ROOT.TH2F(f"Evt{evtNumber}_Cer",    "Cherenkov;X;Y",
                              int(iX_max-iX_min), iX_min, iX_max,
                              int(iY_max-iY_min), iY_min, iY_max)
        h2_Sci     = ROOT.TH2F(f"Evt{evtNumber}_Sci",    "Scintillator;X;Y",
                              int(iX_max-iX_min), iX_min, iX_max,
                              int(iY_max-iY_min), iY_min, iY_max)
        h2_Cer_3mm = ROOT.TH2F(f"Evt{evtNumber}_Cer_3mm", "", 
                              int(iX_max-iX_min), iX_min, iX_max,
                              int((iY_max-iY_min)*4), iY_min, iY_max)
        h2_Sci_3mm = ROOT.TH2F(f"Evt{evtNumber}_Sci_3mm", "", 
                              int(iX_max-iX_min), iX_min, iX_max,
                              int((iY_max-iY_min)*4), iY_min, iY_max)

        # Fill energies into histograms
        for F in FERSBoards.values():
            arr64 = getattr(tree, f"FERS_Board{F.boardNo}_energyHG")
            for tx, ty in F.GetListOfTowers():
                cer_name = F.GetChannelByTower(tx,ty,True).GetHGChannelName()
                sci_name = F.GetChannelByTower(tx,ty,False).GetHGChannelName()
                cer_idx  = int(cer_name.rsplit("_",1)[1])
                sci_idx  = int(sci_name.rsplit("_",1)[1])
                eCer = arr64[cer_idx]
                eSci = arr64[sci_idx]
                if not F.is6mm:
                    print(f"  → filling 3 mm hist for Board{F.boardNo}")
                    
                    print(f"  Board{F.boardNo} ({tx},{ty}): eCer={eCer:.1f}, eSci={eSci:.1f}")

                    h2_Cer_3mm.Fill(tx,ty,eCer)
                    h2_Sci_3mm.Fill(tx,ty,eSci)
                else:
                    h2_Cer   .Fill(tx,ty,eCer)
                    h2_Sci   .Fill(tx,ty,eSci)


        hists_eventdisplay += [h2_Cer, h2_Cer_3mm, h2_Sci, h2_Sci_3mm]

        # Base label for annotations
        # give yourself a little more room on the left…
        ROOT.gStyle.SetPadLeftMargin(0.15)

        # then shift the box right:
        labelBase = ROOT.TPaveText(0.12, 0.73, 0, 0.88, "NDC")
        labelBase.SetFillColorAlpha(0,0); labelBase.SetBorderSize(0)
        labelBase.SetTextFont(42); labelBase.SetTextSize(0.04)
        labelBase.AddText(f"Run: {runNumber}")
        labelBase.AddText(f"Event: {evtNumber}")

        boardDrawables = getBoardDrawables(FERSBoards)

        # Draw Cherenkov display
        labelCer = labelBase.Clone("lblCer")
        labelCer.AddText("Cerenkov")
        DrawHistos(
            [h2_Cer, h2_Cer_3mm], "",
            iX_min, iX_max, "iX",
            iY_min, iY_max, "iY",
            f"event_display_Evt{evtNumber}_Cer",
            dology=False,
            drawoptions=["COLZ,text","COLZ,text"],
            zmin=50.0, zmax=3000.0,
            doth2=True, W_ref=W_ref,
            extraToDraw=[labelCer] + boardDrawables,
            outdir=evdisp_dir
        )
        plots_eventdisplay.append(f"event_display_Evt{evtNumber}_Cer.png")

        # Draw Scintillator display
        labelSci = labelBase.Clone("lblSci")
        labelSci.AddText("Scintillator")
        DrawHistos(
            [h2_Sci, h2_Sci_3mm], "",
            iX_min, iX_max, "iX",
            iY_min, iY_max, "iY",
            f"event_display_Evt{evtNumber}_Sci",
            dology=False,
                drawoptions=["COLZ,text","COLZ,text"],
                zmin=50.0, zmax=8000.0,
                doth2=True, W_ref=W_ref,
            extraToDraw=[labelSci] + boardDrawables,
            outdir=evdisp_dir
        )
        plots_eventdisplay.append(f"event_display_Evt{evtNumber}_Sci.png")

        # Pulse shapes for DRS boards
        for D in DRSBoards.values():
            bNo = D.boardNo
            for tx, ty in D.GetListOfTowers():
                sx, sy = number2string(tx), number2string(ty)
                for var in ("Cer","Sci"):
                    chan = D.GetChannelByTower(tx,ty, isCer=(var=="Cer"))
                    pulse = getattr(tree, chan.GetChannelName())
                    length = len(pulse)
                    h_p = ROOT.TH1F(
                        f"pulse_Evt{evtNumber}_B{bNo}_{var}_{sx}_{sy}",
                        f"Pulse {var} (B{bNo},{sx},{sy});Time;Amp", length, 0, length
                    )
                    for i, amp in enumerate(pulse):
                        h_p.Fill(i, amp)
                    hists_pulse_shapes.append(h_p)

                pCer, pSci = hists_pulse_shapes[-2], hists_pulse_shapes[-1]
                binCer, binSci = pCer.GetMaximumBin(), pSci.GetMaximumBin()
                dT = (binSci - binCer) * 0.2

                lblP = ROOT.TPaveText(0.20,0.65,0.60,0.90,"NDC")
                lblP.SetFillColorAlpha(0,0); lblP.SetBorderSize(0)
                lblP.SetTextFont(42); lblP.SetTextSize(0.04)
                lblP.AddText(f"Evt {evtNumber}, B{bNo}, ({sx},{sy})")
                lblP.AddText(f"Cer peak bin: {binCer}")
                lblP.AddText(f"Sci peak bin: {binSci}")
                lblP.AddText(f"Δt = {dT:.2f} ns")

                DrawHistos(
                    [pCer, pSci], ["Cer","Sci"],
                    0, length, "TS", 0, None, "Amplitude",
                    f"pulse_shape_Evt{evtNumber}_B{bNo}_{sx}_{sy}",
                    dology=False, mycolors=[2,4], drawashist=True,
                    extraToDraw=lblP, outdir=pulse_dir
                )
                plots_pulse_shapes.append(
                    f"pulse_shape_Evt{evtNumber}_B{bNo}_{sx}_{sy}.png"
                )

    # Write a single unified HTML viewer with both Event and Pulse tabs
    all_html = os.path.join("html", "viewer.html")
    # Note: your generate_html signature already takes pulse_files
    generate_html(
        png_files     = plots_eventdisplay,
        png_dir       = evdisp_dir,
        pulse_files   = plots_pulse_shapes,
        plots_per_row = 2,
        output_html   = all_html
    )

    # Save ROOT histograms
    out_evroot = infilename.replace(".root","_event_display.root")
    with ROOT.TFile(out_evroot, "RECREATE") as of:
        print(f"Writing event histos to {out_evroot}")
        for h in hists_eventdisplay:
            h.SetDirectory(of); h.Write()

    out_psroot = infilename.replace(".root","_pulse_shapes.root")
    with ROOT.TFile(out_psroot, "RECREATE") as of:
        print(f"Writing pulse histos to {out_psroot}")
        for h in hists_pulse_shapes:
            h.SetDirectory(of); h.Write()

    print(f"Done in {time.time()-start_time:.2f}s")


if __name__ == "__main__":
    infile = sys.argv[1] if len(sys.argv)>1 else "/home/michaelod/DREAMView/run0624_250611172809.root"
    print(f"Processing {infile}")
    makeEventDisplays(infile)
