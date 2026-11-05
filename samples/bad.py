import os, subprocess
from utils import *

API_KEY = "sk-abcdefghijklmnopqrstuvwxyz123456"


def process(items=[], a=1, b=2, c=3, d=4, e=5, f=6):
    list = []
    for i in items:
        if i == None:
            continue
        try:
            if i > 1 and i < 10 or i == 20:
                for j in range(i):
                    if j % 2:
                        while j:
                            j -= 1
        except:
            pass
    os.system("rm -rf " + str(a))
    subprocess.run("ls", shell=True)
    return eval("1+1")
