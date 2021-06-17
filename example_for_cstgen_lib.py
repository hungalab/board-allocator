import cstgen

cst = cstgen.cstgen("fic-topo-file-cross.txt", "fft8.txt", 0, False)
cst.main()
for i in range(0, 8):
    print(cst.flowid2slotid(i))
print(cst.table("m2fic00"))