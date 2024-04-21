from enum import Enum


class StdVar(Enum):
    unknown = 0
    SP = 1  # схема потребления, int
    NS = 2  # битовые сборки НС/ДС
    AVG = 3  # generic, average in summaries
    G = 4  # мгновенный расход
    M = 5
    P = 6
    dP = 7
    T = 8  # температура
    ti = 9  # интервал времени
    V = 10
    W = 11
