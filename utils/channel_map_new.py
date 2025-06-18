import numpy as np
from utils.CaloXChannel import FERSBoard, DRSBoard

def buildFERSBoards(run=583):
    """
    Build the full 14-board FERS layout (as in run 583) regardless of run number.
    """
    # two base prototypes
    base_6mm = FERSBoard(boardNo=-1, is6mm=True)
    base_3mm = FERSBoard(boardNo=-1, is6mm=False)

    # instantiate all 14 boards
    FERSBoards = {
        f"Board{n}": (base_6mm.copy(boardNo=n) if n not in (6,7)
                     else base_3mm.copy(boardNo=n))
        for n in (0,1,2,3,4,5,6,7,8,9,10,11,12,13)
    }

    # now apply the positional offsets exactly as run 583
    for ix in range(4):
        for iy in range(16):
            # shorthand
            fb = FERSBoards

            fb["Board0"][ix,iy].iTowerX -= 12; fb["Board0"][ix,iy].iTowerY += 6
            fb["Board1"][ix,iy].iTowerX -=  8; fb["Board1"][ix,iy].iTowerY +=10
            fb["Board2"][ix,iy].iTowerX -=  4; fb["Board2"][ix,iy].iTowerY +=10
            fb["Board3"][ix,iy].iTowerX +=   0; fb["Board3"][ix,iy].iTowerY +=12
            fb["Board4"][ix,iy].iTowerX +=   4; fb["Board4"][ix,iy].iTowerY +=10
            fb["Board5"][ix,iy].iTowerX +=   8; fb["Board5"][ix,iy].iTowerY +=10

            fb["Board8"][ix,iy].iTowerX -=   8; fb["Board8"][ix,iy].iTowerY += 2
            fb["Board9"][ix,iy].iTowerX -=   4; fb["Board9"][ix,iy].iTowerY += 2
            fb["Board10"][ix,iy].iTowerX +=  0; fb["Board10"][ix,iy].iTowerY += 0
            fb["Board11"][ix,iy].iTowerX +=  4; fb["Board11"][ix,iy].iTowerY += 2
            fb["Board12"][ix,iy].iTowerX +=  8; fb["Board12"][ix,iy].iTowerY += 2

            # the two 3 mm boards
            fb["Board13"][ix,iy].iTowerX += 12; fb["Board13"][ix,iy].iTowerY += 6
            fb["Board7"][ ix,iy].iTowerX +=  2; fb["Board7"][ ix,iy].iTowerY +=4.25
            fb["Board6"][ ix,iy].iTowerX +=  0; fb["Board6"][ ix,iy].iTowerY +=4.25

    return FERSBoards

def buildDRSBoards(run=None):
    """
    Build a generic 2-board DRS layout (same for all runs).
    """
    base = DRSBoard(boardNo=-1)
    DRSBoards = {
        "Board0": base.copy(boardNo=0),
        "Board2": base.copy(boardNo=2),
    }
    # shift board2 down by 4 in Y
    for ix in range(4):
        for iy in range(8):
            DRSBoards["Board2"][ix,iy].iTowerY -= 4

    return DRSBoards

if __name__ == "__main__":
    fers = buildFERSBoards()
    drs  = buildDRSBoards()
    print("FERS:", sorted(fers.keys()))
    print("DRS: ", sorted(drs.keys()))
