#!/usr/bin/env python
from ase.io import read,write
import sys
import os
os.system("if [ -f ase_out.xyz ]; then rm ase_out.xyz; fi")

traj=read(sys.argv[1],index=":")
for atoms in traj:
    forces=atoms.get_forces()
    if(forces.max()<100 and forces.min()>-100):
        write("ase_out.xyz",atoms,append=True)
