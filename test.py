
from tkinter import *
import tkinter as tk
import math
from ib_insync.contract import *  # noqa
from ib_insync import *


ib = IB().connect(host="127.0.0.1", port=7496, clientId=1)

contract = Index("DAX")
print(ib.qualifyContracts(Index("DAX")))