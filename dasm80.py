#
#   Z80 disassembler
#

import getopt
import os
import sys

buffer = bytearray(0x10000)
jumplabel = [False] * 0x10000
label = [False] * 0x10000
location = 0
opcode = 0
flags = ''

def fetch():
    global buffer, location
    c = buffer[location]
    location += 1
    return c

def byte():
    operand = fetch()
    return f'{operand:0={2 + (operand >= 0xa0)}x}h'

def sbyte():
    operand = (lambda x : x & 0x7f | -(x & 0x80))(fetch())
    return f'{operand:0=+3x}h'

def word():
    global jumplabel, label, flags
    operand = fetch() | fetch() << 8
    if 'B' in flags:
        jumplabel[operand] = True
    else:
        label[operand] = True
    return f'L{operand:0=4x}'

def relative():
    global jumplabel, label, location, flags
    operand = (lambda x : x & 0x7f | -(x & 0x80))(fetch()) + location & 0xffff
    jumplabel[operand] = True
    return f'L{operand:0=4x}'

table_fdcb = {
0x06: # RLC (IY+d)
    ('',   'RLC\t(IY{})'),
0x0e: # RRC (IY+d)
    ('',   'RRC\t(IY{})'),
0x16: # RL (IY+d)
    ('',   'RL\t(IY{})'),
0x1e: # RR (IY+d)
    ('',   'RR\t(IY{})'),
0x26: # SLA (IY+d)
    ('',   'SLA\t(IY{})'),
0x2e: # SRA (IY+d)
    ('',   'SRA\t(IY{})'),
0x3e: # SRL (IY+d)
    ('',   'SRL\t(IY{})'),
0x46: # BIT 0,(IY+d)
    ('',   'BIT\t0,(IY{})'),
0x4e: # BIT 1,(IY+d)
    ('',   'BIT\t1,(IY{})'),
0x56: # BIT 2,(IY+d)
    ('',   'BIT\t2,(IY{})'),
0x5e: # BIT 3,(IY+d)
    ('',   'BIT\t3,(IY{})'),
0x66: # BIT 4,(IY+d)
    ('',   'BIT\t4,(IY{})'),
0x6e: # BIT 5,(IY+d)
    ('',   'BIT\t5,(IY{})'),
0x76: # BIT 6,(IY+d)
    ('',   'BIT\t6,(IY{})'),
0x7e: # BIT 7,(IY+d)
    ('',   'BIT\t7,(IY{})'),
0x86: # RES 0,(IY+d)
    ('',   'RES\t0,(IY{})'),
0x8e: # RES 1,(IY+d)
    ('',   'RES\t1,(IY{})'),
0x96: # RES 2,(IY+d)
    ('',   'RES\t2,(IY{})'),
0x9e: # RES 3,(IY+d)
    ('',   'RES\t3,(IY{})'),
0xa6: # RES 4,(IY+d)
    ('',   'RES\t4,(IY{})'),
0xae: # RES 5,(IY+d)
    ('',   'RES\t5,(IY{})'),
0xb6: # RES 6,(IY+d)
    ('',   'RES\t6,(IY{})'),
0xbe: # RES 7,(IY+d)
    ('',   'RES\t7,(IY{})'),
0xc6: # SET 0,(IY+d)
    ('',   'SET\t0,(IY{})'),
0xce: # SET 1,(IY+d)
    ('',   'SET\t1,(IY{})'),
0xd6: # SET 2,(IY+d)
    ('',   'SET\t2,(IY{})'),
0xde: # SET 3,(IY+d)
    ('',   'SET\t3,(IY{})'),
0xe6: # SET 4,(IY+d)
    ('',   'SET\t4,(IY{})'),
0xee: # SET 5,(IY+d)
    ('',   'SET\t5,(IY{})'),
0xf6: # SET 6,(IY+d)
    ('',   'SET\t6,(IY{})'),
0xfe: # SET 7,(IY+d)
    ('',   'SET\t7,(IY{})'),
}

def op_fdcb():
    global table_fdcb
    d = sbyte()
    opcode = fetch()
    if opcode not in table_fdcb:
        return ''
    return table_fdcb[opcode][1].lower().format(d)

table_ddcb = {
0x06: # RLC (IX+d)
    ('',   'RLC\t(IX{})'),
0x0e: # RRC (IX+d)
    ('',   'RRC\t(IX{})'),
0x16: # RL (IX+d)
    ('',   'RL\t(IX{})'),
0x1e: # RR (IX+d)
    ('',   'RR\t(IX{})'),
0x26: # SLA (IX+d)
    ('',   'SLA\t(IX{})'),
0x2e: # SRA (IX+d)
    ('',   'SRA\t(IX{})'),
0x3e: # SRL (IX+d)
    ('',   'SRL\t(IX{})'),
0x46: # BIT 0,(IX+d)
    ('',   'BIT\t0,(IX{})'),
0x4e: # BIT 1,(IX+d)
    ('',   'BIT\t1,(IX{})'),
0x56: # BIT 2,(IX+d)
    ('',   'BIT\t2,(IX{})'),
0x5e: # BIT 3,(IX+d)
    ('',   'BIT\t3,(IX{})'),
0x66: # BIT 4,(IX+d)
    ('',   'BIT\t4,(IX{})'),
0x6e: # BIT 5,(IX+d)
    ('',   'BIT\t5,(IX{})'),
0x76: # BIT 6,(IX+d)
    ('',   'BIT\t6,(IX{})'),
0x7e: # BIT 7,(IX+d)
    ('',   'BIT\t7,(IX{})'),
0x86: # RES 0,(IX+d)
    ('',   'RES\t0,(IX{})'),
0x8e: # RES 1,(IX+d)
    ('',   'RES\t1,(IX{})'),
0x96: # RES 2,(IX+d)
    ('',   'RES\t2,(IX{})'),
0x9e: # RES 3,(IX+d)
    ('',   'RES\t3,(IX{})'),
0xa6: # RES 4,(IX+d)
    ('',   'RES\t4,(IX{})'),
0xae: # RES 5,(IX+d)
    ('',   'RES\t5,(IX{})'),
0xb6: # RES 6,(IX+d)
    ('',   'RES\t6,(IX{})'),
0xbe: # RES 7,(IX+d)
    ('',   'RES\t7,(IX{})'),
0xc6: # SET 0,(IX+d)
    ('',   'SET\t0,(IX{})'),
0xce: # SET 1,(IX+d)
    ('',   'SET\t1,(IX{})'),
0xd6: # SET 2,(IX+d)
    ('',   'SET\t2,(IX{})'),
0xde: # SET 3,(IX+d)
    ('',   'SET\t3,(IX{})'),
0xe6: # SET 4,(IX+d)
    ('',   'SET\t4,(IX{})'),
0xee: # SET 5,(IX+d)
    ('',   'SET\t5,(IX{})'),
0xf6: # SET 6,(IX+d)
    ('',   'SET\t6,(IX{})'),
0xfe: # SET 7,(IX+d)
    ('',   'SET\t7,(IX{})'),
}

def op_ddcb():
    global table_ddcb
    d = sbyte()
    opcode = fetch()
    if opcode not in table_ddcb:
        return ''
    return table_ddcb[opcode][1].lower().format(d)

table_fd = {
0x09: # ADD IY,BC
    ('',   'ADD\tIY,BC'),
0x19: # ADD IY,DE
    ('',   'ADD\tIY,DE'),
0x21: # LD IY,nn
    ('',   'LD\tIY,{}',      word),
0x22: # LD (nn),IY
    ('',   'LD\t({}),IY',    word),
0x23: # INC IY
    ('',   'INC\tIY'),
0x24: # INC IYH (undefined operation)
    ('',   'INC\tIYH'),
0x25: # DEC IYH (undefined operation)
    ('',   'DEC\tIYH'),
0x26: # LD IYH,n (undefined operation)
    ('',   'LD\tIYH,{}',     byte),
0x29: # ADD IY,IY
    ('',   'ADD\tIY,IY'),
0x2a: # LD IY,(nn)
    ('',   'LD\tIY,({})',    word),
0x2b: # DEC IY
    ('',   'DEC\tIY'),
0x2c: # INC IYL (undefined operation)
    ('',   'INC\tIYL'),
0x2d: # DEC IYL (undefined operation)
    ('',   'DEC\tIYL'),
0x2e: # LD IYL,n (undefined operation)
    ('',   'LD\tIYL,{}',     byte),
0x34: # INC (IY+d)
    ('',   'INC\t(IY{})',    sbyte),
0x35: # DEC (IY+d)
    ('',   'DEC\t(IY{})',    sbyte),
0x36: # LD (IY+d),n
    ('',   'LD\t(IY{}),{}',  sbyte, byte),
0x39: # ADD IY,SP
    ('',   'ADD\tIY,SP'),
0x44: # LD B,IYH (undefined operation)
    ('',   'LD\tB,IYH'),
0x45: # LD B,IYL (undefined operation)
    ('',   'LD\tB,IYL'),
0x46: # LD B,(IY+d)
    ('',   'LD\tB,(IY{})',   sbyte),
0x4c: # LD C,IYH (undefined operation)
    ('',   'LD\tC,IYH'),
0x4d: # LD C,IYL (undefined operation)
    ('',   'LD\tC,IYL'),
0x4e: # LD C,(IY+d)
    ('',   'LD\tC,(IY{})',   sbyte),
0x54: # LD D,IYH (undefined operation)
    ('',   'LD\tD,IYH'),
0x55: # LD D,IYL (undefined operation)
    ('',   'LD\tD,IYL'),
0x56: # LD D,(IY+d)
    ('',   'LD\tD,(IY{})',   sbyte),
0x5c: # LD E,IYH (undefined operation)
    ('',   'LD\tE,IYH'),
0x5d: # LD E,IYL (undefined operation)
    ('',   'LD\tE,IYL'),
0x5e: # LD E,(IY+d)
    ('',   'LD\tE,(IY{})',   sbyte),
0x60: # LD IYH,B (undefined operation)
    ('',   'LD\tIYH,B'),
0x61: # LD IYH,C (undefined operation)
    ('',   'LD\tIYH,C'),
0x62: # LD IYH,D (undefined operation)
    ('',   'LD\tIYH,D'),
0x63: # LD IYH,E (undefined operation)
    ('',   'LD\tIYH,E'),
0x66: # LD H,(IY+d)
    ('',   'LD\tH,(IY{})',   sbyte),
0x67: # LD IYH,A (undefined operation)
    ('',   'LD\tIYH,A'),
0x68: # LD IYL,B (undefined operation)
    ('',   'LD\tIYL,B'),
0x69: # LD IYL,C (undefined operation)
    ('',   'LD\tIYL,C'),
0x6a: # LD IYL,D (undefined operation)
    ('',   'LD\tIYL,D'),
0x6b: # LD IYL,E (undefined operation)
    ('',   'LD\tIYL,E'),
0x6e: # LD L,(IY+d)
    ('',   'LD\tL,(IY{})',   sbyte),
0x6f: # LD IYL,A (undefined operation)
    ('',   'LD\tIYL,A'),
0x70: # LD (IY+d),B
    ('',   'LD\t(IY{}),B',   sbyte),
0x71: # LD (IY+d),C
    ('',   'LD\t(IY{}),C',   sbyte),
0x72: # LD (IY+d),D
    ('',   'LD\t(IY{}),D',   sbyte),
0x73: # LD (IY+d),E
    ('',   'LD\t(IY{}),E',   sbyte),
0x74: # LD (IY+d),H
    ('',   'LD\t(IY{}),H',   sbyte),
0x75: # LD (IY+d),L
    ('',   'LD\t(IY{}),L',   sbyte),
0x77: # LD (IY+d),A
    ('',   'LD\t(IY{}),A',   sbyte),
0x7c: # LD A,IYH (undefined operation)
    ('',   'LD\tA,IYH'),
0x7d: # LD A,IYL (undefined operation)
    ('',   'LD\tA,IYL'),
0x7e: # LD A,(IY+d)
    ('',   'LD\tA,(IY{})',   sbyte),
0x84: # ADD A,IYH (undefined operation)
    ('',   'ADD\tA,IYH'),
0x85: # ADD A,IYL (undefined operation)
    ('',   'ADD\tA,IYL'),
0x86: # ADD A,(IY+d)
    ('',   'ADD\tA,(IY{})',  sbyte),
0x8c: # ADC A,IYH (undefined operation)
    ('',   'ADC\tA,IYH'),
0x8d: # ADC A,IYL (undefined operation)
    ('',   'ADC\tA,IYL'),
0x8e: # ADC A,(IY+d)
    ('',   'ADC\tA,(IY{})',  sbyte),
0x94: # SUB IYH (undefined operation)
    ('',   'SUB\tIYH'),
0x95: # SUB IYL (undefined operation)
    ('',   'SUB\tIYL'),
0x96: # SUB (IY+d)
    ('',   'SUB\t(IY{})',    sbyte),
0x9c: # SBC A,IYH (undefined operation)
    ('',   'SBC\tA,IYH'),
0x9d: # SBC A,IYL (undefined operation)
    ('',   'SBC\tA,IYL'),
0x9e: # SBC A,(IY+d)
    ('',   'SBC\tA,(IY{})',  sbyte),
0xa4: # AND IYH (undefined operation)
    ('',   'AND\tIYH'),
0xa5: # AND IYL (undefined operation)
    ('',   'AND\tIYL'),
0xa6: # AND (IY+d)
    ('',   'AND\t(IY{})',    sbyte),
0xac: # XOR IYH (undefined operation)
    ('',   'XOR\tIYH'),
0xad: # XOR IYL (undefined operation)
    ('',   'XOR\tIYL'),
0xae: # XOR (IY+d)
    ('',   'XOR\t(IY{})',    sbyte),
0xb4: # OR IYH (undefined operation)
    ('',   'OR\tIYH'),
0xb5: # OR IYL (undefined operation)
    ('',   'OR\tIYL'),
0xb6: # OR (IY+d)
    ('',   'OR\t(IY{})',     sbyte),
0xbc: # CP IYH (undefined operation)
    ('',   'CP\tIYH'),
0xbd: # CP IYL (undefined operation)
    ('',   'CP\tIYL'),
0xbe: # CP (IY+d)
    ('',   'CP\t(IY{})',     sbyte),
0xcb:
    ('',   '{}',             op_fdcb),
0xe1: # POP IY
    ('',   'POP\tIY'),
0xe3: # EX (SP),IY
    ('',   'EX\t(SP),IY'),
0xe5: # PUSH IY
    ('',   'PUSH\tIY'),
0xe9: # JP (IY)
    ('A',  'JP\t(IY)'),
0xf9: # LD SP,IY
    ('',   'LD\tSP,IY'),
}

def op_fd():
    global flags, table_fd
    opcode = fetch()
    if opcode not in table_fd:
        return ''
    t = table_fd[opcode]
    flags = t[0]
    return t[1].lower().format(*[f() for f in t[2:]])

table_ed = {
0x40: # IN B,(C)
    ('',   'IN\tB,(C)'),
0x41: # OUT (C),B
    ('',   'OUT\t(C),B'),
0x42: # SBC HL,BC
    ('',   'SBC\tHL,BC'),
0x43: # LD (nn),BC
    ('',   'LD\t({}),BC', word),
0x44: # NEG
    ('',   'NEG'),
0x45: # RETN
    ('A',  'RETN'),
0x46: # IM 0
    ('',   'IM\t0'),
0x47: # LD I,A
    ('',   'LD\tI,A'),
0x48: # IN C,(C)
    ('',   'IN\tC,(C)'),
0x49: # OUT (C),C
    ('',   'OUT\t(C),C'),
0x4a: # ADC HL,BC
    ('',   'ADC\tHL,BC'),
0x4b: # LD BC,(nn)
    ('',   'LD\tBC,({})', word),
0x4d: # RETI
    ('A',  'RETI'),
0x4f: # LD R,A
    ('',   'LD\tR,A'),
0x50: # IN D,(C)
    ('',   'IN\tD,(C)'),
0x51: # OUT (C),D
    ('',   'OUT\t(C),D'),
0x52: # SBC HL,DE
    ('',   'SBC\tHL,DE'),
0x53: # LD (nn),DE
    ('',   'LD\t({}),DE', word),
0x56: # IM 1
    ('',   'IM\t1'),
0x57: # LD A,I
    ('',   'LD\tA,I'),
0x58: # IN E,(C)
    ('',   'IN\tE,(C)'),
0x59: # OUT (C),E
    ('',   'OUT\t(C),E'),
0x5a: # ADC HL,DE
    ('',   'ADC\tHL,DE'),
0x5b: # LD DE,(nn)
    ('',   'LD\tDE,({})', word),
0x5e: # IM 2
    ('',   'IM\t2'),
0x5f: # LD A,R
    ('',   'LD\tA,R'),
0x60: # IN H,(C)
    ('',   'IN\tH,(C)'),
0x61: # OUT (C),H
    ('',   'OUT\t(C),H'),
0x62: # SBC HL,HL
    ('',   'SBC\tHL,HL'),
0x67: # RRD
    ('',   'RRD'),
0x68: # IN L,(C)
    ('',   'IN\tL,(C)'),
0x69: # OUT (C),L
    ('',   'OUT\t(C),L'),
0x6a: # ADC HL,HL
    ('',   'ADC\tHL,HL'),
0x6f: # RLD
    ('',   'RLD'),
0x72: # SBC HL,SP
    ('',   'SBC\tHL,SP'),
0x73: # LD (nn),SP
    ('',   'LD\t({}),SP', word),
0x78: # IN A,(C)
    ('',   'IN\tA,(C)'),
0x79: # OUT (C),A
    ('',   'OUT\t(C),A'),
0x7a: # ADC HL,SP
    ('',   'ADC\tHL,SP'),
0x7b: # LD SP,(nn)
    ('',   'LD\tSP,({})', word),
0xa0: # LDI
    ('',   'LDI'),
0xa1: # CPI
    ('',   'CPI'),
0xa2: # INI
    ('',   'INI'),
0xa3: # OUTI
    ('',   'OUTI'),
0xa8: # LDD
    ('',   'LDD'),
0xa9: # CPD
    ('',   'CPD'),
0xaa: # IND
    ('',   'IND'),
0xab: # OUTD
    ('',   'OUTD'),
0xb0: # LDIR
    ('',   'LDIR'),
0xb1: # CPIR
    ('',   'CPIR'),
0xb2: # INIR
    ('',   'INIR'),
0xb3: # OTIR
    ('',   'OTIR'),
0xb8: # LDDR
    ('',   'LDDR'),
0xb9: # CPDR
    ('',   'CPDR'),
0xba: # INDR
    ('',   'INDR'),
0xbb: # OTDR
    ('',   'OTDR'),
}

def op_ed():
    global flags, table_ed
    opcode = fetch()
    if opcode not in table_ed:
        return ''
    t = table_ed[opcode]
    flags = t[0]
    return t[1].lower().format(*[f() for f in t[2:]])

table_dd = {
0x09: # ADD IX,BC
    ('',   'ADD\tIX,BC'),
0x19: # ADD IX,DE
    ('',   'ADD\tIX,DE'),
0x21: # LD IX,nn
    ('',   'LD\tIX,{}',      word),
0x22: # LD (nn),IX
    ('',   'LD\t({}),IX',    word),
0x23: # INC IX
    ('',   'INC\tIX'),
0x24: # INC IXH (undefined operation)
    ('',   'INC\tIXH'),
0x25: # DEC IXH (undefined operation)
    ('',   'DEC\tIXH'),
0x26: # LD IXH,n (undefined operation)
    ('',   'LD\tIXH,{}',     byte),
0x29: # ADD IX,IX
    ('',   'ADD\tIX,IX'),
0x2a: # LD IX,(nn)
    ('',   'LD\tIX,({})',    word),
0x2b: # DEC IX
    ('',   'DEC\tIX'),
0x2c: # INC IXL (undefined operation)
    ('',   'INC\tIXL'),
0x2d: # DEC IXL (undefined operation)
    ('',   'DEC\tIXL'),
0x2e: # LD IXL,n (undefined operation)
    ('',   'LD\tIXL,{}',     byte),
0x34: # INC (IX+d)
    ('',   'INC\t(IX{})',    sbyte),
0x35: # DEC (IX+d)
    ('',   'DEC\t(IX{})',    sbyte),
0x36: # LD (IX+d),n
    ('',   'LD\t(IX{}),{}',  sbyte, byte),
0x39: # ADD IX,SP
    ('',   'ADD\tIX,SP'),
0x44: # LD B,IXH (undefined operation)
    ('',   'LD\tB,IXH'),
0x45: # LD B,IXL (undefined operation)
    ('',   'LD\tB,IXL'),
0x46: # LD B,(IX+d)
    ('',   'LD\tB,(IX{})',   sbyte),
0x4c: # LD C,IXH (undefined operation)
    ('',   'LD\tC,IXH'),
0x4d: # LD C,IXL (undefined operation)
    ('',   'LD\tC,IXL'),
0x4e: # LD C,(IX+d)
    ('',   'LD\tC,(IX{})',   sbyte),
0x54: # LD D,IXH (undefined operation)
    ('',   'LD\tD,IXH'),
0x55: # LD D,IXL (undefined operation)
    ('',   'LD\tD,IXL'),
0x56: # LD D,(IX+d)
    ('',   'LD\tD,(IX{})',   sbyte),
0x5c: # LD E,IXH (undefined operation)
    ('',   'LD\tE,IXH'),
0x5d: # LD E,IXL (undefined operation)
    ('',   'LD\tE,IXL'),
0x5e: # LD E,(IX+d)
    ('',   'LD\tE,(IX{})',   sbyte),
0x60: # LD IXH,B (undefined operation)
    ('',   'LD\tIXH,B'),
0x61: # LD IXH,C (undefined operation)
    ('',   'LD\tIXH,C'),
0x62: # LD IXH,D (undefined operation)
    ('',   'LD\tIXH,D'),
0x63: # LD IXH,E (undefined operation)
    ('',   'LD\tIXH,E'),
0x66: # LD H,(IX+d)
    ('',   'LD\tH,(IX{})',   sbyte),
0x67: # LD IXH,A (undefined operation)
    ('',   'LD\tIXH,A'),
0x68: # LD IXL,B (undefined operation)
    ('',   'LD\tIXL,B'),
0x69: # LD IXL,C (undefined operation)
    ('',   'LD\tIXL,C'),
0x6a: # LD IXL,D (undefined operation)
    ('',   'LD\tIXL,D'),
0x6b: # LD IXL,E (undefined operation)
    ('',   'LD\tIXL,E'),
0x6e: # LD L,(IX+d)
    ('',   'LD\tL,(IX{})',   sbyte),
0x6f: # LD IXL,A (undefined operation)
    ('',   'LD\tIXL,A'),
0x70: # LD (IX+d),B
    ('',   'LD\t(IX{}),B',   sbyte),
0x71: # LD (IX+d),C
    ('',   'LD\t(IX{}),C',   sbyte),
0x72: # LD (IX+d),D
    ('',   'LD\t(IX{}),D',   sbyte),
0x73: # LD (IX+d),E
    ('',   'LD\t(IX{}),E',   sbyte),
0x74: # LD (IX+d),H
    ('',   'LD\t(IX{}),H',   sbyte),
0x75: # LD (IX+d),L
    ('',   'LD\t(IX{}),L',   sbyte),
0x77: # LD (IX+d),A
    ('',   'LD\t(IX{}),A',   sbyte),
0x7c: # LD A,IXH (undefined operation)
    ('',   'LD\tA,IXH'),
0x7d: # LD A,IXL (undefined operation)
    ('',   'LD\tA,IXL'),
0x7e: # LD A,(IX+d)
    ('',   'LD\tA,(IX{})',   sbyte),
0x84: # ADD A,IXH (undefined operation)
    ('',   'ADD\tA,IXH'),
0x85: # ADD A,IXL (undefined operation)
    ('',   'ADD\tA,IXL'),
0x86: # ADD A,(IX+d)
    ('',   'ADD\tA,(IX{})',  sbyte),
0x8c: # ADC A,IXH (undefined operation)
    ('',   'ADC\tA,IXH'),
0x8d: # ADC A,IXL (undefined operation)
    ('',   'ADC\tA,IXL'),
0x8e: # ADC A,(IX+d)
    ('',   'ADC\tA,(IX{})',  sbyte),
0x94: # SUB IXH (undefined operation)
    ('',   'SUB\tIXH'),
0x95: # SUB IXL (undefined operation)
    ('',   'SUB\tIXL'),
0x96: # SUB (IX+d)
    ('',   'SUB\t(IX{})',    sbyte),
0x9c: # SBC A,IXH (undefined operation)
    ('',   'SBC\tA,IXH'),
0x9d: # SBC A,IXL (undefined operation)
    ('',   'SBC\tA,IXL'),
0x9e: # SBC A,(IX+d)
    ('',   'SBC\tA,(IX{})',  sbyte),
0xa4: # AND IXH (undefined operation)
    ('',   'AND\tIXH'),
0xa5: # AND IXL (undefined operation)
    ('',   'AND\tIXL'),
0xa6: # AND (IX+d)
    ('',   'AND\t(IX{})',    sbyte),
0xac: # XOR IXH (undefined operation)
    ('',   'XOR\tIXH'),
0xad: # XOR IXL (undefined operation)
    ('',   'XOR\tIXL'),
0xae: # XOR (IX+d)
    ('',   'XOR\t(IX{})',    sbyte),
0xb4: # OR IXH (undefined operation)
    ('',   'OR\tIXH'),
0xb5: # OR IXL (undefined operation)
    ('',   'OR\tIXL'),
0xb6: # OR (IX+d)
    ('',   'OR\t(IX{})',     sbyte),
0xbc: # CP IXH (undefined operation)
    ('',   'CP\tIXH'),
0xbd: # CP IXL (undefined operation)
    ('',   'CP\tIXL'),
0xbe: # CP (IX+d)
    ('',   'CP\t(IX{})',     sbyte),
0xcb:
    ('',   '{}',             op_ddcb),
0xe1: # POP IX
    ('',   'POP\tIX'),
0xe3: # EX (SP),IX
    ('',   'EX\t(SP),IX'),
0xe5: # PUSH IX
    ('',   'PUSH\tIX'),
0xe9: # JP (IX)
    ('A',  'JP\t(IX)'),
0xf9: # LD SP,IX
    ('',   'LD\tSP,IX'),
}

def op_dd():
    global flags, table_dd
    opcode = fetch()
    if opcode not in table_dd:
        return ''
    t = table_dd[opcode]
    flags = t[0]
    return t[1].lower().format(*[f() for f in t[2:]])

table_cb = {
0x00: # RLC B
    ('',   'RLC\tB'),
0x01: # RLC C
    ('',   'RLC\tC'),
0x02: # RLC D
    ('',   'RLC\tD'),
0x03: # RLC E
    ('',   'RLC\tE'),
0x04: # RLC H
    ('',   'RLC\tH'),
0x05: # RLC L
    ('',   'RLC\tL'),
0x06: # RLC (HL)
    ('',   'RLC\t(HL)'),
0x07: # RLC A
    ('',   'RLC\tA'),
0x08: # RRC B
    ('',   'RRC\tB'),
0x09: # RRC C
    ('',   'RRC\tC'),
0x0a: # RRC D
    ('',   'RRC\tD'),
0x0b: # RRC E
    ('',   'RRC\tE'),
0x0c: # RRC H
    ('',   'RRC\tH'),
0x0d: # RRC L
    ('',   'RRC\tL'),
0x0e: # RRC (HL)
    ('',   'RRC\t(HL)'),
0x0f: # RRC A
    ('',   'RRC\tA'),
0x10: # RL B
    ('',   'RL\tB'),
0x11: # RL C
    ('',   'RL\tC'),
0x12: # RL D
    ('',   'RL\tD'),
0x13: # RL E
    ('',   'RL\tE'),
0x14: # RL H
    ('',   'RL\tH'),
0x15: # RL L
    ('',   'RL\tL'),
0x16: # RL (HL)
    ('',   'RL\t(HL)'),
0x17: # RL A
    ('',   'RL\tA'),
0x18: # RR B
    ('',   'RR\tB'),
0x19: # RR C
    ('',   'RR\tC'),
0x1a: # RR D
    ('',   'RR\tD'),
0x1b: # RR E
    ('',   'RR\tE'),
0x1c: # RR H
    ('',   'RR\tH'),
0x1d: # RR L
    ('',   'RR\tL'),
0x1e: # RR (HL)
    ('',   'RR\t(HL)'),
0x1f: # RR A
    ('',   'RR\tA'),
0x20: # SLA B
    ('',   'SLA\tB'),
0x21: # SLA C
    ('',   'SLA\tC'),
0x22: # SLA D
    ('',   'SLA\tD'),
0x23: # SLA E
    ('',   'SLA\tE'),
0x24: # SLA H
    ('',   'SLA\tH'),
0x25: # SLA L
    ('',   'SLA\tL'),
0x26: # SLA (HL)
    ('',   'SLA\t(HL)'),
0x27: # SLA A
    ('',   'SLA\tA'),
0x28: # SRA B
    ('',   'SRA\tB'),
0x29: # SRA C
    ('',   'SRA\tC'),
0x2a: # SRA D
    ('',   'SRA\tD'),
0x2b: # SRA E
    ('',   'SRA\tE'),
0x2c: # SRA H
    ('',   'SRA\tH'),
0x2d: # SRA L
    ('',   'SRA\tL'),
0x2e: # SRA (HL)
    ('',   'SRA\t(HL)'),
0x2f: # SRA A
    ('',   'SRA\tA'),
0x38: # SRL B
    ('',   'SRL\tB'),
0x39: # SRL C
    ('',   'SRL\tC'),
0x3a: # SRL D
    ('',   'SRL\tD'),
0x3b: # SRL E
    ('',   'SRL\tE'),
0x3c: # SRL H
    ('',   'SRL\tH'),
0x3d: # SRL L
    ('',   'SRL\tL'),
0x3e: # SRL (HL)
    ('',   'SRL\t(HL)'),
0x3f: # SRL A
    ('',   'SRL\tA'),
0x40: # BIT 0,B
    ('',   'BIT\t0,B'),
0x41: # BIT 0,C
    ('',   'BIT\t0,C'),
0x42: # BIT 0,D
    ('',   'BIT\t0,D'),
0x43: # BIT 0,E
    ('',   'BIT\t0,E'),
0x44: # BIT 0,H
    ('',   'BIT\t0,H'),
0x45: # BIT 0,L
    ('',   'BIT\t0,L'),
0x46: # BIT 0,(HL)
    ('',   'BIT\t0,(HL)'),
0x47: # BIT 0,A
    ('',   'BIT\t0,A'),
0x48: # BIT 1,B
    ('',   'BIT\t1,B'),
0x49: # BIT 1,C
    ('',   'BIT\t1,C'),
0x4a: # BIT 1,D
    ('',   'BIT\t1,D'),
0x4b: # BIT 1,E
    ('',   'BIT\t1,E'),
0x4c: # BIT 1,H
    ('',   'BIT\t1,H'),
0x4d: # BIT 1,L
    ('',   'BIT\t1,L'),
0x4e: # BIT 1,(HL)
    ('',   'BIT\t1,(HL)'),
0x4f: # BIT 1,A
    ('',   'BIT\t1,A'),
0x50: # BIT 2,B
    ('',   'BIT\t2,B'),
0x51: # BIT 2,C
    ('',   'BIT\t2,C'),
0x52: # BIT 2,D
    ('',   'BIT\t2,D'),
0x53: # BIT 2,E
    ('',   'BIT\t2,E'),
0x54: # BIT 2,H
    ('',   'BIT\t2,H'),
0x55: # BIT 2,L
    ('',   'BIT\t2,L'),
0x56: # BIT 2,(HL)
    ('',   'BIT\t2,(HL)'),
0x57: # BIT 2,A
    ('',   'BIT\t2,A'),
0x58: # BIT 3,B
    ('',   'BIT\t3,B'),
0x59: # BIT 3,C
    ('',   'BIT\t3,C'),
0x5a: # BIT 3,D
    ('',   'BIT\t3,D'),
0x5b: # BIT 3,E
    ('',   'BIT\t3,E'),
0x5c: # BIT 3,H
    ('',   'BIT\t3,H'),
0x5d: # BIT 3,L
    ('',   'BIT\t3,L'),
0x5e: # BIT 3,(HL)
    ('',   'BIT\t3,(HL)'),
0x5f: # BIT 3,A
    ('',   'BIT\t3,A'),
0x60: # BIT 4,B
    ('',   'BIT\t4,B'),
0x61: # BIT 4,C
    ('',   'BIT\t4,C'),
0x62: # BIT 4,D
    ('',   'BIT\t4,D'),
0x63: # BIT 4,E
    ('',   'BIT\t4,E'),
0x64: # BIT 4,H
    ('',   'BIT\t4,H'),
0x65: # BIT 4,L
    ('',   'BIT\t4,L'),
0x66: # BIT 4,(HL)
    ('',   'BIT\t4,(HL)'),
0x67: # BIT 4,A
    ('',   'BIT\t4,A'),
0x68: # BIT 5,B
    ('',   'BIT\t5,B'),
0x69: # BIT 5,C
    ('',   'BIT\t5,C'),
0x6a: # BIT 5,D
    ('',   'BIT\t5,D'),
0x6b: # BIT 5,E
    ('',   'BIT\t5,E'),
0x6c: # BIT 5,H
    ('',   'BIT\t5,H'),
0x6d: # BIT 5,L
    ('',   'BIT\t5,L'),
0x6e: # BIT 5,(HL)
    ('',   'BIT\t5,(HL)'),
0x6f: # BIT 5,A
    ('',   'BIT\t5,A'),
0x70: # BIT 6,B
    ('',   'BIT\t6,B'),
0x71: # BIT 6,C
    ('',   'BIT\t6,C'),
0x72: # BIT 6,D
    ('',   'BIT\t6,D'),
0x73: # BIT 6,E
    ('',   'BIT\t6,E'),
0x74: # BIT 6,H
    ('',   'BIT\t6,H'),
0x75: # BIT 6,L
    ('',   'BIT\t6,L'),
0x76: # BIT 6,(HL)
    ('',   'BIT\t6,(HL)'),
0x77: # BIT 6,A
    ('',   'BIT\t6,A'),
0x78: # BIT 7,B
    ('',   'BIT\t7,B'),
0x79: # BIT 7,C
    ('',   'BIT\t7,C'),
0x7a: # BIT 7,D
    ('',   'BIT\t7,D'),
0x7b: # BIT 7,E
    ('',   'BIT\t7,E'),
0x7c: # BIT 7,H
    ('',   'BIT\t7,H'),
0x7d: # BIT 7,L
    ('',   'BIT\t7,L'),
0x7e: # BIT 7,(HL)
    ('',   'BIT\t7,(HL)'),
0x7f: # BIT 7,A
    ('',   'BIT\t7,A'),
0x80: # RES 0,B
    ('',   'RES\t0,B'),
0x81: # RES 0,C
    ('',   'RES\t0,C'),
0x82: # RES 0,D
    ('',   'RES\t0,D'),
0x83: # RES 0,E
    ('',   'RES\t0,E'),
0x84: # RES 0,H
    ('',   'RES\t0,H'),
0x85: # RES 0,L
    ('',   'RES\t0,L'),
0x86: # RES 0,(HL)
    ('',   'RES\t0,(HL)'),
0x87: # RES 0,A
    ('',   'RES\t0,A'),
0x88: # RES 1,B
    ('',   'RES\t1,B'),
0x89: # RES 1,C
    ('',   'RES\t1,C'),
0x8a: # RES 1,D
    ('',   'RES\t1,D'),
0x8b: # RES 1,E
    ('',   'RES\t1,E'),
0x8c: # RES 1,H
    ('',   'RES\t1,H'),
0x8d: # RES 1,L
    ('',   'RES\t1,L'),
0x8e: # RES 1,(HL)
    ('',   'RES\t1,(HL)'),
0x8f: # RES 1,A
    ('',   'RES\t1,A'),
0x90: # RES 2,B
    ('',   'RES\t2,B'),
0x91: # RES 2,C
    ('',   'RES\t2,C'),
0x92: # RES 2,D
    ('',   'RES\t2,D'),
0x93: # RES 2,E
    ('',   'RES\t2,E'),
0x94: # RES 2,H
    ('',   'RES\t2,H'),
0x95: # RES 2,L
    ('',   'RES\t2,L'),
0x96: # RES 2,(HL)
    ('',   'RES\t2,(HL)'),
0x97: # RES 2,A
    ('',   'RES\t2,A'),
0x98: # RES 3,B
    ('',   'RES\t3,B'),
0x99: # RES 3,C
    ('',   'RES\t3,C'),
0x9a: # RES 3,D
    ('',   'RES\t3,D'),
0x9b: # RES 3,E
    ('',   'RES\t3,E'),
0x9c: # RES 3,H
    ('',   'RES\t3,H'),
0x9d: # RES 3,L
    ('',   'RES\t3,L'),
0x9e: # RES 3,(HL)
    ('',   'RES\t3,(HL)'),
0x9f: # RES 3,A
    ('',   'RES\t3,A'),
0xa0: # RES 4,B
    ('',   'RES\t4,B'),
0xa1: # RES 4,C
    ('',   'RES\t4,C'),
0xa2: # RES 4,D
    ('',   'RES\t4,D'),
0xa3: # RES 4,E
    ('',   'RES\t4,E'),
0xa4: # RES 4,H
    ('',   'RES\t4,H'),
0xa5: # RES 4,L
    ('',   'RES\t4,L'),
0xa6: # RES 4,(HL)
    ('',   'RES\t4,(HL)'),
0xa7: # RES 4,A
    ('',   'RES\t4,A'),
0xa8: # RES 5,B
    ('',   'RES\t5,B'),
0xa9: # RES 5,C
    ('',   'RES\t5,C'),
0xaa: # RES 5,D
    ('',   'RES\t5,D'),
0xab: # RES 5,E
    ('',   'RES\t5,E'),
0xac: # RES 5,H
    ('',   'RES\t5,H'),
0xad: # RES 5,L
    ('',   'RES\t5,L'),
0xae: # RES 5,(HL)
    ('',   'RES\t5,(HL)'),
0xaf: # RES 5,A
    ('',   'RES\t5,A'),
0xb0: # RES 6,B
    ('',   'RES\t6,B'),
0xb1: # RES 6,C
    ('',   'RES\t6,C'),
0xb2: # RES 6,D
    ('',   'RES\t6,D'),
0xb3: # RES 6,E
    ('',   'RES\t6,E'),
0xb4: # RES 6,H
    ('',   'RES\t6,H'),
0xb5: # RES 6,L
    ('',   'RES\t6,L'),
0xb6: # RES 6,(HL)
    ('',   'RES\t6,(HL)'),
0xb7: # RES 6,A
    ('',   'RES\t6,A'),
0xb8: # RES 7,B
    ('',   'RES\t7,B'),
0xb9: # RES 7,C
    ('',   'RES\t7,C'),
0xba: # RES 7,D
    ('',   'RES\t7,D'),
0xbb: # RES 7,E
    ('',   'RES\t7,E'),
0xbc: # RES 7,H
    ('',   'RES\t7,H'),
0xbd: # RES 7,L
    ('',   'RES\t7,L'),
0xbe: # RES 7,(HL)
    ('',   'RES\t7,(HL)'),
0xbf: # RES 7,A
    ('',   'RES\t7,A'),
0xc0: # SET 0,B
    ('',   'SET\t0,B'),
0xc1: # SET 0,C
    ('',   'SET\t0,C'),
0xc2: # SET 0,D
    ('',   'SET\t0,D'),
0xc3: # SET 0,E
    ('',   'SET\t0,E'),
0xc4: # SET 0,H
    ('',   'SET\t0,H'),
0xc5: # SET 0,L
    ('',   'SET\t0,L'),
0xc6: # SET 0,(HL)
    ('',   'SET\t0,(HL)'),
0xc7: # SET 0,A
    ('',   'SET\t0,A'),
0xc8: # SET 1,B
    ('',   'SET\t1,B'),
0xc9: # SET 1,C
    ('',   'SET\t1,C'),
0xca: # SET 1,D
    ('',   'SET\t1,D'),
0xcb: # SET 1,E
    ('',   'SET\t1,E'),
0xcc: # SET 1,H
    ('',   'SET\t1,H'),
0xcd: # SET 1,L
    ('',   'SET\t1,L'),
0xce: # SET 1,(HL)
    ('',   'SET\t1,(HL)'),
0xcf: # SET 1,A
    ('',   'SET\t1,A'),
0xd0: # SET 2,B
    ('',   'SET\t2,B'),
0xd1: # SET 2,C
    ('',   'SET\t2,C'),
0xd2: # SET 2,D
    ('',   'SET\t2,D'),
0xd3: # SET 2,E
    ('',   'SET\t2,E'),
0xd4: # SET 2,H
    ('',   'SET\t2,H'),
0xd5: # SET 2,L
    ('',   'SET\t2,L'),
0xd6: # SET 2,(HL)
    ('',   'SET\t2,(HL)'),
0xd7: # SET 2,A
    ('',   'SET\t2,A'),
0xd8: # SET 3,B
    ('',   'SET\t3,B'),
0xd9: # SET 3,C
    ('',   'SET\t3,C'),
0xda: # SET 3,D
    ('',   'SET\t3,D'),
0xdb: # SET 3,E
    ('',   'SET\t3,E'),
0xdc: # SET 3,H
    ('',   'SET\t3,H'),
0xdd: # SET 3,L
    ('',   'SET\t3,L'),
0xde: # SET 3,(HL)
    ('',   'SET\t3,(HL)'),
0xdf: # SET 3,A
    ('',   'SET\t3,A'),
0xe0: # SET 4,B
    ('',   'SET\t4,B'),
0xe1: # SET 4,C
    ('',   'SET\t4,C'),
0xe2: # SET 4,D
    ('',   'SET\t4,D'),
0xe3: # SET 4,E
    ('',   'SET\t4,E'),
0xe4: # SET 4,H
    ('',   'SET\t4,H'),
0xe5: # SET 4,L
    ('',   'SET\t4,L'),
0xe6: # SET 4,(HL)
    ('',   'SET\t4,(HL)'),
0xe7: # SET 4,A
    ('',   'SET\t4,A'),
0xe8: # SET 5,B
    ('',   'SET\t5,B'),
0xe9: # SET 5,C
    ('',   'SET\t5,C'),
0xea: # SET 5,D
    ('',   'SET\t5,D'),
0xeb: # SET 5,E
    ('',   'SET\t5,E'),
0xec: # SET 5,H
    ('',   'SET\t5,H'),
0xed: # SET 5,L
    ('',   'SET\t5,L'),
0xee: # SET 5,(HL)
    ('',   'SET\t5,(HL)'),
0xef: # SET 5,A
    ('',   'SET\t5,A'),
0xf0: # SET 6,B
    ('',   'SET\t6,B'),
0xf1: # SET 6,C
    ('',   'SET\t6,C'),
0xf2: # SET 6,D
    ('',   'SET\t6,D'),
0xf3: # SET 6,E
    ('',   'SET\t6,E'),
0xf4: # SET 6,H
    ('',   'SET\t6,H'),
0xf5: # SET 6,L
    ('',   'SET\t6,L'),
0xf6: # SET 6,(HL)
    ('',   'SET\t6,(HL)'),
0xf7: # SET 6,A
    ('',   'SET\t6,A'),
0xf8: # SET 7,B
    ('',   'SET\t7,B'),
0xf9: # SET 7,C
    ('',   'SET\t7,C'),
0xfa: # SET 7,D
    ('',   'SET\t7,D'),
0xfb: # SET 7,E
    ('',   'SET\t7,E'),
0xfc: # SET 7,H
    ('',   'SET\t7,H'),
0xfd: # SET 7,L
    ('',   'SET\t7,L'),
0xfe: # SET 7,(HL)
    ('',   'SET\t7,(HL)'),
0xff: # SET 7,A
    ('',   'SET\t7,A'),
}

def op_cb():
    global table_cb
    opcode = fetch()
    if opcode not in table_cb:
        return ''
    return table_cb[opcode][1].lower()

table = {
0x00: # NOP
    ('',   'NOP'),
0x01: # LD BC,nn
    ('',   'LD\tBC,{}',   word),
0x02: # LD (BC),A
    ('',   'LD\t(BC),A'),
0x03: # INC BC
    ('',   'INC\tBC'),
0x04: # INC B
    ('',   'INC\tB'),
0x05: # DEC B
    ('',   'DEC\tB'),
0x06: # LD B,n
    ('',   'LD\tB,{}',    byte),
0x07: # RLCA
    ('',   'RLCA'),
0x08: # EX AF,AF'
    ('',   'EX\tAF,AF\''),
0x09: # ADD HL,BC
    ('',   'ADD\tHL,BC'),
0x0a: # LD A,(BC)
    ('',   'LD\tA,(BC)'),
0x0b: # DEC BC
    ('',   'DEC\tBC'),
0x0c: # INC C
    ('',   'INC\tC'),
0x0d: # DEC C
    ('',   'DEC\tC'),
0x0e: # LD C,n
    ('',   'LD\tC,{}',    byte),
0x0f: # RRCA
    ('',   'RRCA'),
0x10: # DJNZ e
    ('B',  'DJNZ\t{}',    relative),
0x11: # LD DE,nn
    ('',   'LD\tDE,{}',   word),
0x12: # LD (DE),A
    ('',   'LD\t(DE),A'),
0x13: # INC DE
    ('',   'INC\tDE'),
0x14: # INC D
    ('',   'INC\tD'),
0x15: # DEC D
    ('',   'DEC\tD'),
0x16: # LD D,n
    ('',   'LD\tD,{}',    byte),
0x17: # RLA
    ('',   'RLA'),
0x18: # JR e
    ('AB', 'JR\t{}',      relative),
0x19: # ADD HL,DE
    ('',   'ADD\tHL,DE'),
0x1a: # LD A,(DE)
    ('',   'LD\tA,(DE)'),
0x1b: # DEC DE
    ('',   'DEC\tDE'),
0x1c: # INC E
    ('',   'INC\tE'),
0x1d: # DEC E
    ('',   'DEC\tE'),
0x1e: # LD E,n
    ('',   'LD\tE,{}',    byte),
0x1f: # RRA
    ('',   'RRA'),
0x20: # JR NZ,e
    ('B',  'JR\tNZ,{}',   relative),
0x21: # LD HL,nn
    ('',   'LD\tHL,{}',   word),
0x22: # LD (nn),HL
    ('',   'LD\t({}),HL', word),
0x23: # INC HL
    ('',   'INC\tHL'),
0x24: # INC H
    ('',   'INC\tH'),
0x25: # DEC H
    ('',   'DEC\tH'),
0x26: # LD H,n
    ('',   'LD\tH,{}',    byte),
0x27: # DAA
    ('',   'DAA'),
0x28: # JR Z,e
    ('B',  'JR\tZ,{}',    relative),
0x29: # ADD HL,HL
    ('',   'ADD\tHL,HL'),
0x2a: # LD HL,(nn)
    ('',   'LD\tHL,({})', word),
0x2b: # DEC HL
    ('',   'DEC\tHL'),
0x2c: # INC L
    ('',   'INC\tL'),
0x2d: # DEC L
    ('',   'DEC\tL'),
0x2e: # LD L,n
    ('',   'LD\tL,{}',    byte),
0x2f: # CPL
    ('',   'CPL'),
0x30: # JR NC,e
    ('B',  'JR\tNC,{}',   relative),
0x31: # LD SP,nn
    ('',   'LD\tSP,{}',   word),
0x32: # LD (nn),A
    ('',   'LD\t({}),A',  word),
0x33: # INC SP
    ('',   'INC\tSP'),
0x34: # INC (HL)
    ('',   'INC\t(HL)'),
0x35: # DEC (HL)
    ('',   'DEC\t(HL)'),
0x36: # LD (HL),n
    ('',   'LD\t(HL),{}', byte),
0x37: # SCF
    ('',   'SCF'),
0x38: # JR C,e
    ('B',  'JR\tC,{}',    relative),
0x39: # ADD HL,SP
    ('',   'ADD\tHL,SP'),
0x3a: # LD A,(nn)
    ('',   'LD\tA,({})',  word),
0x3b: # DEC SP
    ('',   'DEC\tSP'),
0x3c: # INC A
    ('',   'INC\tA'),
0x3d: # DEC A
    ('',   'DEC\tA'),
0x3e: # LD A,n
    ('',   'LD\tA,{}',    byte),
0x3f: # CCF
    ('',   'CCF'),
0x40: # LD B,B
    ('',   'LD\tB,B'),
0x41: # LD B,C
    ('',   'LD\tB,C'),
0x42: # LD B,D
    ('',   'LD\tB,D'),
0x43: # LD B,E
    ('',   'LD\tB,E'),
0x44: # LD B,H
    ('',   'LD\tB,H'),
0x45: # LD B,L
    ('',   'LD\tB,L'),
0x46: # LD B,(HL)
    ('',   'LD\tB,(HL)'),
0x47: # LD B,A
    ('',   'LD\tB,A'),
0x48: # LD C,B
    ('',   'LD\tC,B'),
0x49: # LD C,C
    ('',   'LD\tC,C'),
0x4a: # LD C,D
    ('',   'LD\tC,D'),
0x4b: # LD C,E
    ('',   'LD\tC,E'),
0x4c: # LD C,H
    ('',   'LD\tC,H'),
0x4d: # LD C,L
    ('',   'LD\tC,L'),
0x4e: # LD C,(HL)
    ('',   'LD\tC,(HL)'),
0x4f: # LD C,A
    ('',   'LD\tC,A'),
0x50: # LD D,B
    ('',   'LD\tD,B'),
0x51: # LD D,C
    ('',   'LD\tD,C'),
0x52: # LD D,D
    ('',   'LD\tD,D'),
0x53: # LD D,E
    ('',   'LD\tD,E'),
0x54: # LD D,H
    ('',   'LD\tD,H'),
0x55: # LD D,L
    ('',   'LD\tD,L'),
0x56: # LD D,(HL)
    ('',   'LD\tD,(HL)'),
0x57: # LD D,A
    ('',   'LD\tD,A'),
0x58: # LD E,B
    ('',   'LD\tE,B'),
0x59: # LD E,C
    ('',   'LD\tE,C'),
0x5a: # LD E,D
    ('',   'LD\tE,D'),
0x5b: # LD E,E
    ('',   'LD\tE,E'),
0x5c: # LD E,H
    ('',   'LD\tE,H'),
0x5d: # LD E,L
    ('',   'LD\tE,L'),
0x5e: # LD E,(HL)
    ('',   'LD\tE,(HL)'),
0x5f: # LD E,A
    ('',   'LD\tE,A'),
0x60: # LD H,B
    ('',   'LD\tH,B'),
0x61: # LD H,C
    ('',   'LD\tH,C'),
0x62: # LD H,D
    ('',   'LD\tH,D'),
0x63: # LD H,E
    ('',   'LD\tH,E'),
0x64: # LD H,H
    ('',   'LD\tH,H'),
0x65: # LD H,L
    ('',   'LD\tH,L'),
0x66: # LD H,(HL)
    ('',   'LD\tH,(HL)'),
0x67: # LD H,A
    ('',   'LD\tH,A'),
0x68: # LD L,B
    ('',   'LD\tL,B'),
0x69: # LD L,C
    ('',   'LD\tL,C'),
0x6a: # LD L,D
    ('',   'LD\tL,D'),
0x6b: # LD L,E
    ('',   'LD\tL,E'),
0x6c: # LD L,H
    ('',   'LD\tL,H'),
0x6d: # LD L,L
    ('',   'LD\tL,L'),
0x6e: # LD L,(HL)
    ('',   'LD\tL,(HL)'),
0x6f: # LD L,A
    ('',   'LD\tL,A'),
0x70: # LD (HL),B
    ('',   'LD\t(HL),B'),
0x71: # LD (HL),C
    ('',   'LD\t(HL),C'),
0x72: # LD (HL),D
    ('',   'LD\t(HL),D'),
0x73: # LD (HL),E
    ('',   'LD\t(HL),E'),
0x74: # LD (HL),H
    ('',   'LD\t(HL),H'),
0x75: # LD (HL),L
    ('',   'LD\t(HL),L'),
0x76: # HALT
    ('',   'HALT'),
0x77: # LD (HL),A
    ('',   'LD\t(HL),A'),
0x78: # LD A,B
    ('',   'LD\tA,B'),
0x79: # LD A,C
    ('',   'LD\tA,C'),
0x7a: # LD A,D
    ('',   'LD\tA,D'),
0x7b: # LD A,E
    ('',   'LD\tA,E'),
0x7c: # LD A,H
    ('',   'LD\tA,H'),
0x7d: # LD A,L
    ('',   'LD\tA,L'),
0x7e: # LD A,(HL)
    ('',   'LD\tA,(HL)'),
0x7f: # LD A,A
    ('',   'LD\tA,A'),
0x80: # ADD A,B
    ('',   'ADD\tA,B'),
0x81: # ADD A,C
    ('',   'ADD\tA,C'),
0x82: # ADD A,D
    ('',   'ADD\tA,D'),
0x83: # ADD A,E
    ('',   'ADD\tA,E'),
0x84: # ADD A,H
    ('',   'ADD\tA,H'),
0x85: # ADD A,L
    ('',   'ADD\tA,L'),
0x86: # ADD A,(HL)
    ('',   'ADD\tA,(HL)'),
0x87: # ADD A,A
    ('',   'ADD\tA,A'),
0x88: # ADC A,B
    ('',   'ADC\tA,B'),
0x89: # ADC A,C
    ('',   'ADC\tA,C'),
0x8a: # ADC A,D
    ('',   'ADC\tA,D'),
0x8b: # ADC A,E
    ('',   'ADC\tA,E'),
0x8c: # ADC A,H
    ('',   'ADC\tA,H'),
0x8d: # ADC A,L
    ('',   'ADC\tA,L'),
0x8e: # ADC A,(HL)
    ('',   'ADC\tA,(HL)'),
0x8f: # ADC A,A
    ('',   'ADC\tA,A'),
0x90: # SUB B
    ('',   'SUB\tB'),
0x91: # SUB C
    ('',   'SUB\tC'),
0x92: # SUB D
    ('',   'SUB\tD'),
0x93: # SUB E
    ('',   'SUB\tE'),
0x94: # SUB H
    ('',   'SUB\tH'),
0x95: # SUB L
    ('',   'SUB\tL'),
0x96: # SUB (HL)
    ('',   'SUB\t(HL)'),
0x97: # SUB A
    ('',   'SUB\tA'),
0x98: # SBC A,B
    ('',   'SBC\tA,B'),
0x99: # SBC A,C
    ('',   'SBC\tA,C'),
0x9a: # SBC A,D
    ('',   'SBC\tA,D'),
0x9b: # SBC A,E
    ('',   'SBC\tA,E'),
0x9c: # SBC A,H
    ('',   'SBC\tA,H'),
0x9d: # SBC A,L
    ('',   'SBC\tA,L'),
0x9e: # SBC A,(HL)
    ('',   'SBC\tA,(HL)'),
0x9f: # SBC A,A
    ('',   'SBC\tA,A'),
0xa0: # AND B
    ('',   'AND\tB'),
0xa1: # AND C
    ('',   'AND\tC'),
0xa2: # AND D
    ('',   'AND\tD'),
0xa3: # AND E
    ('',   'AND\tE'),
0xa4: # AND H
    ('',   'AND\tH'),
0xa5: # AND L
    ('',   'AND\tL'),
0xa6: # AND (HL)
    ('',   'AND\t(HL)'),
0xa7: # AND A
    ('',   'AND\tA'),
0xa8: # XOR B
    ('',   'XOR\tB'),
0xa9: # XOR C
    ('',   'XOR\tC'),
0xaa: # XOR D
    ('',   'XOR\tD'),
0xab: # XOR E
    ('',   'XOR\tE'),
0xac: # XOR H
    ('',   'XOR\tH'),
0xad: # XOR L
    ('',   'XOR\tL'),
0xae: # XOR (HL)
    ('',   'XOR\t(HL)'),
0xaf: # XOR A
    ('',   'XOR\tA'),
0xb0: # OR B
    ('',   'OR\tB'),
0xb1: # OR C
    ('',   'OR\tC'),
0xb2: # OR D
    ('',   'OR\tD'),
0xb3: # OR E
    ('',   'OR\tE'),
0xb4: # OR H
    ('',   'OR\tH'),
0xb5: # OR L
    ('',   'OR\tL'),
0xb6: # OR (HL)
    ('',   'OR\t(HL)'),
0xb7: # OR A
    ('',   'OR\tA'),
0xb8: # CP B
    ('',   'CP\tB'),
0xb9: # CP C
    ('',   'CP\tC'),
0xba: # CP D
    ('',   'CP\tD'),
0xbb: # CP E
    ('',   'CP\tE'),
0xbc: # CP H
    ('',   'CP\tH'),
0xbd: # CP L
    ('',   'CP\tL'),
0xbe: # CP (HL)
    ('',   'CP\t(HL)'),
0xbf: # CP A
    ('',   'CP\tA'),
0xc0: # RET NZ
    ('',   'RET\tNZ'),
0xc1: # POP BC
    ('',   'POP\tBC'),
0xc2: # JP NZ,nn
    ('B',  'JP\tNZ,{}',   word),
0xc3: # JP nn
    ('AB', 'JP\t{}',      word),
0xc4: # CALL NZ,nn
    ('B',  'CALL\tNZ,{}', word),
0xc5: # PUSH BC
    ('',   'PUSH\tBC'),
0xc6: # ADD A,n
    ('',   'ADD\tA,{}',   byte),
0xc7: # RST 00H
    ('',   'RST\t00H'),
0xc8: # RET Z
    ('',   'RET\tZ'),
0xc9: # RET
    ('A',  'RET'),
0xca: # JP Z,nn
    ('B',  'JP\tZ,{}',    word),
0xcb:
    ('',   '{}',          op_cb),
0xcc: # CALL Z,nn
    ('B',  'CALL\tZ,{}',  word),
0xcd: # CALL nn
    ('B',  'CALL\t{}',    word),
0xce: # ADC A,n
    ('',   'ADC\tA,{}',   byte),
0xcf: # RST 08H
    ('',   'RST\t08H'),
0xd0: # RET NC
    ('',   'RET\tNC'),
0xd1: # POP DE
    ('',   'POP\tDE'),
0xd2: # JP NC,nn
    ('B',  'JP\tNC,{}',   word),
0xd3: # OUT n,A
    ('B',  'OUT\t{},A',   byte),
0xd4: # CALL NC,nn
    ('',   'CALL\tNC,{}', word),
0xd5: # PUSH DE
    ('',   'PUSH\tDE'),
0xd6: # SUB n
    ('',   'SUB\t{}',     byte),
0xd7: # RST 10H
    ('',   'RST\t10H'),
0xd8: # RET C
    ('',   'RET\tC'),
0xd9: # EXX
    ('',   'EXX'),
0xda: # JP C,nn
    ('B',  'JP\tC,{}',    word),
0xdb: # IN A,n
    ('',   'IN\tA,{}',    byte),
0xdc: # CALL C,nn
    ('B',  'CALL\tC,{}',  word),
0xdd:
    ('',   '{}',          op_dd),
0xde: # SBC A,n
    ('',   'SBC\tA,{}',   byte),
0xdf: # RST 18H
    ('',   'RST\t18H'),
0xe0: # RET PO
    ('',   'RET\tPO'),
0xe1: # POP HL
    ('',   'POP\tHL'),
0xe2: # JP PO,nn
    ('B',  'JP\tPO,{}',   word),
0xe3: # EX (SP),HL
    ('',   'EX\t(SP),HL'),
0xe4: # CALL PO,nn
    ('B',  'CALL\tPO,{}', word),
0xe5: # PUSH HL
    ('',   'PUSH\tHL'),
0xe6: # AND n
    ('',   'AND\t{}',     byte),
0xe7: # RST 20H
    ('',   'RST\t20H'),
0xe8: # RET PE
    ('',   'RET\tPE'),
0xe9: # JP (HL)
    ('A',  'JP\t(HL)'),
0xea: # JP PE,nn
    ('B',  'JP\tPE,{}',   word),
0xeb: # EX DE,HL
    ('',   'EX\tDE,HL'),
0xec: # CALL PE,nn
    ('B',  'CALL\tPE,{}', word),
0xed:
    ('',   '{}',          op_ed),
0xee: # XOR n
    ('',   'XOR\t{}',     byte),
0xef: # RST 28H
    ('',   'RST\t28H'),
0xf0: # RET P
    ('',   'RET\tP'),
0xf1: # POP AF
    ('',   'POP\tAF'),
0xf2: # JP P,nn
    ('B',  'JP\tP,{}',    word),
0xf3: # DI
    ('',   'DI'),
0xf4: # CALL P,nn
    ('B',  'CALL\tP,{}',  word),
0xf5: # PUSH AF
    ('',   'PUSH\tAF'),
0xf6: # OR n
    ('',   'OR\t{}',      byte),
0xf7: # RST 30H
    ('',   'RST\t30H'),
0xf8: # RET M
    ('',   'RET\tM'),
0xf9: # LD SP,HL
    ('',   'LD\tSP,HL'),
0xfa: # JP M,nn
    ('B',  'JP\tM,{}',    word),
0xfb: # EI
    ('',   'EI'),
0xfc: # CALL M,nn
    ('B',  'CALL\tM,{}',  word),
0xfd:
    ('',   '{}',          op_fd),
0xfe: # CP n
    ('',   'CP\t{}',      byte),
0xff: # RST 38H
    ('',   'RST\t38H'),
}

def op():
    global flags, table
    opcode = fetch()
    if opcode not in table:
        flags = ''
        return ''
    t = table[opcode]
    flags = t[0]
    return t[1].lower().format(*[f() for f in t[2:]])

# main
opts, args = getopt.getopt(sys.argv[1:], "e:flo:s:t:")
if len(args) == 0:
    print(f'使い方: {os.path.basename(sys.argv[0])} [オプション] ファイル名')
    print(f'オプション:')
    print(f'  -e <アドレス>   エントリ番地を指定する')
    print(f'  -f              強制的に逆アセンブルする')
    print(f'  -l              アドレスとデータを出力する')
    print(f'  -o <ファイル名> 出力ファイルを指定する(デフォルト:標準出力)')
    print(f'  -s <アドレス>   開始番地を指定する(デフォルト:0)')
    print(f'  -t <ファイル名> ラベルテーブルを使用する')
    sys.exit(0)
remark = {}
code = [False] * 0x10000
string = [False] * 0x10000
bytestring = [False] * 0x10000
pointer = [False] * 0x10000
start = 0
end = 0
listing = False
noentry = True
file = sys.stdout
tablefile = None
for o, a in opts:
    if o == '-e':
        jumplabel[int(a, 0)] = True
        noentry = False
    elif o == '-f':
        code = [True] * 0x10000
    elif o == '-l':
        listing = True
    elif o == '-o':
        file = open(a, 'w', encoding='utf-8')
    elif o == '-s':
        start = int(a, 0)
        end = start
    elif o == '-t':
        tablefile = open(a, 'r', encoding='utf-8')
with open(args[0], 'rb') as f:
    data = f.read()
    buffer[start:] = data
    end = start + len(data)
if tablefile:
    for line in tablefile:
        words = line.split(' ')
        if words[0] == 'b':
            base = int(words[1], 16)
            size = int(words[2], 10) if len(words) > 2 else 1
            bytestring[base:base + size] = [True] * size
        elif words[0] == 'c':
            jumplabel[int(words[1], 16)] = True
            noentry = False
        elif words[0] == 'd':
            label[int(words[1], 16)] = True
        elif words[0] == 'r':
            addr = int(words[1], 16)
            if addr not in remark:
                remark[addr] = []
            remark[addr] += [line[len(words[0] + words[1]) + 2:].rstrip()]
        elif words[0] == 's':
            base = int(words[1], 16)
            size = int(words[2], 10) if len(words) > 2 else 1
            string[base:base + size] = [True] * size
        elif words[0] == 't':
            base = int(words[1], 16)
            size = int(words[2], 10) if len(words) > 2 else 1
            for i in range(base, base + size * 2, 2):
                pointer[i:i + 2] = [True] * 2
                jumplabel[buffer[i] | buffer[i + 1] << 8] = True
            noentry = False
        elif words[0] == 'u':
            base = int(words[1], 16)
            size = int(words[2], 10) if len(words) > 2 else 1
            for i in range(base, base + size * 2, 2):
                pointer[i:i + 2] = [True] * 2
                label[buffer[i] | buffer[i + 1] << 8] = True
        elif words[0] == 'v':
            base = int(words[1], 16)
            size = int(words[2], 10) if len(words) > 2 else 1
            for i in range(base, base + size * 3, 3):
                pointer[i:i + 2] = [True] * 2
                label[buffer[i] | buffer[i + 1] << 8] = True

# path 1
if noentry:
    jumplabel[start] = True
while True:
    location = end
    for i in range(start, end):
        if jumplabel[i] and not code[i]:
            location = i
            break
    if location == end:
        break
    while True:
        base = location
        op()
        code[base:location] = [True] * (location - base)
        if 'A' in flags or location >= end or string[location] or bytestring[location] or pointer[location]:
            break

# path 2
if listing:
    print(f'\t\t\t;-----------------------------------------------', file=file)
    print(f'\t\t\t;\tZ80 disassembler', file=file)
    print(f'\t\t\t;\tfilename: {args[0]}', file=file)
    print(f'\t\t\t;-----------------------------------------------', file=file)
    print(f'\t\t\t\torg\t{start:0={4 + (start >= 0xa000)}x}h', file=file)
    print(f'\t\t\t', file=file)
else:
    print(f';-----------------------------------------------', file=file)
    print(f';\tZ80 disassembler', file=file)
    print(f';\tfilename: {args[0]}', file=file)
    print(f';-----------------------------------------------', file=file)
    print(f'\torg\t{start:0={4 + (start >= 0xa000)}x}h', file=file)
    print(f'', file=file)
location = start
while location < end:
    base = location
    if base in remark:
        for s in remark[base]:
            if listing:
                print(f'{base:0=4X}\t\t\t', end='', file=file)
            print(f';{s}', file=file)
    if code[base]:
        s = op()
        size = location - base
    else:
        s = ''
        size = 1
    if s != '':
        if listing:
            print(f'{base:0=4X} ', end='', file=file)
            location = base
            for i in range(size):
                print(f' {fetch():0=2X}', end='', file=file)
            print('\t\t' if size < 4 else '\t', end='', file=file)
        if jumplabel[base]:
            print(f'L{base:0=4x}:', end='', file=file)
        print('\t' + s, file=file)
    elif string[base]:
        if listing:
            print(f'{base:0=4X}\t\t\t', end='', file=file)
        if label[base]:
            print(f'L{base:0=4x}:', end='', file=file)
        location = base
        print(f'\tdb\t\'{fetch():c}', end='', file=file)
        while location < end and string[location] and not label[location]:
            print(f'{fetch():c}', end='', file=file)
        print('\'', file=file)
    elif bytestring[base]:
        if listing:
            print(f'{base:0=4X}\t\t\t', end='', file=file)
        if label[base]:
            print(f'L{base:0=4x}:', end='', file=file)
        location = base
        c = fetch()
        print(f'\tdb\t${c:0={2 + (c >= 0xa0)}x}', end='', file=file)
        for i in range(7):
            if location >= end or not bytestring[location] or label[location]:
                break
            c = fetch()
            print(f',{c:0={2 + (c >= 0xa0)}x}h', end='', file=file)
        print('', file=file)
    elif pointer[base]:
        if listing:
            print(f'{base:0=4X}\t\t\t', end='', file=file)
        if label[base]:
            print(f'L{base:0=4x}:', end='', file=file)
        location = base
        print(f'\tdw\tL{fetch() | fetch() << 8:0=4x}', end='', file=file)
        for i in range(3):
            if location >= end or not pointer[location] or label[location]:
                break
            print(f',L{fetch() | fetch() << 8:0=4x}', end='', file=file)
        print('', file=file)
    else:
        location = base
        for i in range(size):
            base = location
            c = fetch()
            if listing:
                print(f'{base:0=4X}  {c:0=2X}\t\t', end='', file=file)
            if label[base] or jumplabel[base]:
                print(f'L{base:0=4x}:', end='', file=file)
            print(f'\tdb\t{c:0={2 + (c >= 0xa0)}x}h', end='', file=file)
            if c >= 0x20 and c < 0x7f:
                print(f'\t;\'{c:c}\'', end='', file=file)
            print('', file=file)
if listing:
    print(f'{location & 0xffff:0=4X}\t\t\t', end='', file=file)
print('\tend', file=file)
