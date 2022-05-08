#
#   MC6809 disassembler
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
    return f'${fetch():0=2x}'

def word():
    global jumplabel, label, flags
    operand = fetch() << 8 | fetch()
    if 'B' in flags:
        jumplabel[operand] = True
    else:
        label[operand] = True
    return f'L{operand:0=4x}'

def am_relative():
    global jumplabel, label, location, flags
    operand = (lambda x : x & 0x7f | -(x & 0x80))(fetch()) + location & 0xffff
    if 'B' in flags:
        jumplabel[operand] = True
    else:
        label[operand] = True
    return f'L{operand:0=4x}'

def am_lrelative():
    global jumplabel, label, location, flags
    operand = (fetch() << 8 | fetch()) + location & 0xffff
    if 'B' in flags:
        jumplabel[operand] = True
    else:
        label[operand] = True
    return f'L{operand:0=4x}'

def am_index():
    post = fetch()
    if post & 0x80 and post & 0x1f in [0x07, 0x0a, 0x0e, 0x0f, 0x10, 0x12, 0x17, 0x1a, 0x1e]:
        return ''
    pl = post & 15
    if not post & 0x80:
        d = post & 15 | -(post & 16)
        offset = ('-' if d < 0 else '') + f'${abs(d):0=2x}'
    elif pl == 5:
        offset = 'b'
    elif pl == 6:
        offset = 'a'
    elif pl == 8:
        d = (lambda x : x & 0x7f | -(x & 0x80))(fetch())
        offset = ('-' if d < 0 else '') + f'${abs(d):0=2x}'
    elif pl == 9 or pl == 15:
        offset = word()
    elif pl == 11:
        offset = 'd'
    elif pl == 12:
        offset = am_relative()
    elif pl == 13:
        offset = am_lrelative()
    else:
        offset = ''
    dec = ['', '', '-', '--'][pl] if post & 0x80 and (pl == 2 or pl == 3) else ''
    reg = 'pc' if post & 0x80 and (pl == 0x0c or pl == 0x0d) else ['x', 'y', 'u', 's'][post >> 5 & 3]
    inc = ['+', '++', '', ''][pl] if post & 0x80 and (pl == 0 or pl == 1) else ''
    if not post & 0x80 or not post & 0x10:
        return f'{offset},{dec}{reg}{inc}'
    if pl != 0x0f:
        return f'[{offset},{dec}{reg}{inc}]'
    return f'[{offset}]'

def exg_tfr():
    post = fetch()
    regs = ['d', 'x', 'y', 'u', 's', '', '', '', 'a', 'b', 'cc', 'dp', '', '', '', ''] 
    src = regs[post >> 4]
    dst = regs[post & 15]
    return f'{src},{dst}' if src != '' and dst != '' else ''

def psh_pul():
    global buffer, location
    post = fetch()
    regs = ['cc', 'a', 'b', 'dp', 'x', 'y', 's' if buffer[location - 2] & 2 else 'u', 'pc']
    return ','.join([reg for i, reg in enumerate(regs) if post & 1 << i])

table_11 = {
0x3f: # SWI3
    ('',   'SWI3'),
0x83: # CMPU #nn
    ('',   'CMPU\t#{}',  word),
0x8c: # CMPS #nn
    ('',   'CMPS\t#{}',  word),
0x93: # CMPU <n
    ('',   'CMPU\t<{}',  byte),
0x9c: # CMPS <n
    ('',   'CMPS\t<{}',  byte),
0xa3: # CMPU ,r
    ('',   'CMPU\t{}',   am_index),
0xac: # CMPS ,r
    ('',   'CMPS\t{}',   am_index),
0xb3: # CMPU >nn
    ('',   'CMPU\t{}',   word),
0xbc: # CMPS >nn
    ('',   'CMPS\t{}',   word),
}

def op_11():
    global flags, table_11
    opcode = fetch()
    if opcode not in table_11:
        return ''
    t = table_11[opcode]
    flags = t[0]
    operands = [f() for f in t[2:]]
    return t[1].lower().format(*operands) if '' not in operands else ''

table_10 = {
0x21: # LBRN
    ('B',  'LBRN\t{}',   am_lrelative),
0x22: # LBHI
    ('B',  'LBHI\t{}',   am_lrelative),
0x23: # LBLS
    ('B',  'LBLS\t{}',   am_lrelative),
0x24: # LBHS(LBCC)
    ('B',  'LBCC\t{}',   am_lrelative),
0x25: # LBLO(LBCS)
    ('B',  'LBCS\t{}',   am_lrelative),
0x26: # LBNE
    ('B',  'LBNE\t{}',   am_lrelative),
0x27: # LBEQ
    ('B',  'LBEQ\t{}',   am_lrelative),
0x28: # LBVC
    ('B',  'LBVC\t{}',   am_lrelative),
0x29: # LBVS
    ('B',  'LBVS\t{}',   am_lrelative),
0x2a: # LBPL
    ('B',  'LBPL\t{}',   am_lrelative),
0x2b: # LBMI
    ('B',  'LBMI\t{}',   am_lrelative),
0x2c: # LBGE
    ('B',  'LBGE\t{}',   am_lrelative),
0x2d: # LBLT
    ('B',  'LBLT\t{}',   am_lrelative),
0x2e: # LBGT
    ('B',  'LBGT\t{}',   am_lrelative),
0x2f: # LBLE
    ('B',  'LBLE\t{}',   am_lrelative),
0x3f: # SWI2
    ('',   'SWI2'),
0x83: # CMPD #nn
    ('',   'CMPD\t#{}',  word),
0x8c: # CMPY #nn
    ('',   'CMPY\t#{}',  word),
0x8e: # LDY #nn
    ('',   'LDY\t#{}',   word),
0x93: # CMPD <n
    ('',   'CMPD\t<{}',  byte),
0x9c: # CMPY <n
    ('',   'CMPY\t<{}',  byte),
0x9e: # LDY <n
    ('',   'LDY\t<{}',   byte),
0x9f: # STY <n
    ('',   'STY\t<{}',   byte),
0xa3: # CMPD ,r
    ('',   'CMPD\t{}',   am_index),
0xac: # CMPY ,r
    ('',   'CMPY\t{}',   am_index),
0xae: # LDY ,r
    ('',   'LDY\t{}',    am_index),
0xaf: # STY ,r
    ('',   'STY\t{}',    am_index),
0xb3: # CMPD >nn
    ('',   'CMPD\t{}',   word),
0xbc: # CMPY >nn
    ('',   'CMPY\t{}',   word),
0xbe: # LDY >nn
    ('',   'LDY\t{}',    word),
0xbf: # STY >nn
    ('',   'STY\t{}',    word),
0xce: # LDS #nn
    ('',   'LDS\t#{}',   word),
0xde: # LDS <n
    ('',   'LDS\t<{}',   byte),
0xdf: # STS <n
    ('',   'STS\t<{}',   byte),
0xee: # LDS ,r
    ('',   'LDS\t{}',    am_index),
0xef: # STS ,r
    ('',   'STS\t{}',    am_index),
0xfe: # LDS >nn
    ('',   'LDS\t{}',    word),
0xff: # STS >nn
    ('',   'STS\t{}',    word),
}

def op_10():
    global flags, table_10
    opcode = fetch()
    if opcode not in table_10:
        return ''
    t = table_10[opcode]
    flags = t[0]
    operands = [f() for f in t[2:]]
    return t[1].lower().format(*operands) if '' not in operands else ''

table = {
0x00: # NEG <n
    ('',   'NEG\t<{}',   byte),
0x03: # COM <n
    ('',   'COM\t<{}',   byte),
0x04: # LSR <n
    ('',   'LSR\t<{}',   byte),
0x06: # ROR <n
    ('',   'ROR\t<{}',   byte),
0x07: # ASR <n
    ('',   'ASR\t<{}',   byte),
0x08: # LSL <n
    ('',   'LSL\t<{}',   byte),
0x09: # ROL <n
    ('',   'ROL\t<{}',   byte),
0x0a: # DEC <n
    ('',   'DEC\t<{}',   byte),
0x0c: # INC <n
    ('',   'INC\t<{}',   byte),
0x0d: # TST <n
    ('',   'TST\t<{}',   byte),
0x0e: # JMP <n
    ('A',  'JMP\t<{}',   byte),
0x0f: # CLR <n
    ('',   'CLR\t<{}',   byte),
0x10:
    ('',   '{}',         op_10),
0x11:
    ('',   '{}',         op_11),
0x12: # NOP
    ('',   'NOP'),
0x13: # SYNC
    ('',   'SYNC'),
0x16: # LBRA
    ('AB', 'LBRA\t{}',   am_lrelative),
0x17: # LBSR
    ('B',  'LBSR\t{}',   am_lrelative),
0x19: # DAA
    ('',   'DAA'),
0x1a: # ORCC
    ('',   'ORCC\t#{}',  byte),
0x1c: # ANDCC
    ('',   'ANDCC\t#{}', byte),
0x1d: # SEX
    ('',   'SEX'),
0x1e: # EXG
    ('',   'EXG\t{}',    exg_tfr),
0x1f: # TFR
    ('',   'TFR\t{}',    exg_tfr),
0x20: # BRA
    ('AB', 'BRA\t{}',    am_relative),
0x21: # BRN
    ('B',  'BRN\t{}',    am_relative),
0x22: # BHI
    ('B',  'BHI\t{}',    am_relative),
0x23: # BLS
    ('B',  'BLS\t{}',    am_relative),
0x24: # BHS(BCC)
    ('B',  'BCC\t{}',    am_relative),
0x25: # BLO(BCS)
    ('B',  'BCS\t{}',    am_relative),
0x26: # BNE
    ('B',  'BNE\t{}',    am_relative),
0x27: # BEQ
    ('B',  'BEQ\t{}',    am_relative),
0x28: # BVC
    ('B',  'BVC\t{}',    am_relative),
0x29: # BVS
    ('B',  'BVS\t{}',    am_relative),
0x2a: # BPL
    ('B',  'BPL\t{}',    am_relative),
0x2b: # BMI
    ('B',  'BMI\t{}',    am_relative),
0x2c: # BGE
    ('B',  'BGE\t{}',    am_relative),
0x2d: # BLT
    ('B',  'BLT\t{}',    am_relative),
0x2e: # BGT
    ('B',  'BGT\t{}',    am_relative),
0x2f: # BLE
    ('B',  'BLE\t{}',    am_relative),
0x30: # LEAX
    ('',   'LEAX\t{}',   am_index),
0x31: # LEAY
    ('',   'LEAY\t{}',   am_index),
0x32: # LEAS
    ('',   'LEAS\t{}',   am_index),
0x33: # LEAU
    ('',   'LEAU\t{}',   am_index),
0x34: # PSHS
    ('',   'PSHS\t{}',   psh_pul),
0x35: # PULS
    ('',   'PULS\t{}',   psh_pul),
0x36: # PSHU
    ('',   'PSHU\t{}',   psh_pul),
0x37: # PULU
    ('',   'PULU\t{}',   psh_pul),
0x39: # RTS
    ('A',  'RTS'),
0x3a: # ABX
    ('',   'ABX'),
0x3b: # RTI
    ('A',  'RTI'),
0x3c: # CWAI
    ('',   'CWAI\t#{}',  byte),
0x3d: # MUL
    ('',   'MUL'),
0x3f: # SWI
    ('',   'SWI'),
0x40: # NEGA
    ('',   'NEGA'),
0x43: # COMA
    ('',   'COMA'),
0x44: # LSRA
    ('',   'LSRA'),
0x46: # RORA
    ('',   'RORA'),
0x47: # ASRA
    ('',   'ASRA'),
0x48: # LSLA
    ('',   'LSLA'),
0x49: # ROLA
    ('',   'ROLA'),
0x4a: # DECA
    ('',   'DECA'),
0x4c: # INCA
    ('',   'INCA'),
0x4d: # TSTA
    ('',   'TSTA'),
0x4f: # CLRA
    ('',   'CLRA'),
0x50: # NEGB
    ('',   'NEGB'),
0x53: # COMB
    ('',   'COMB'),
0x54: # LSRB
    ('',   'LSRB'),
0x56: # RORB
    ('',   'RORB'),
0x57: # ASRB
    ('',   'ASRB'),
0x58: # LSLB
    ('',   'LSLB'),
0x59: # ROLB
    ('',   'ROLB'),
0x5a: # DECB
    ('',   'DECB'),
0x5c: # INCB
    ('',   'INCB'),
0x5d: # TSTB
    ('',   'TSTB'),
0x5f: # CLRB
    ('',   'CLRB'),
0x60: # NEG ,r
    ('',   'NEG\t{}',    am_index),
0x63: # COM ,r
    ('',   'COM\t{}',    am_index),
0x64: # LSR ,r
    ('',   'LSR\t{}',    am_index),
0x66: # ROR ,r
    ('',   'ROR\t{}',    am_index),
0x67: # ASR ,r
    ('',   'ASR\t{}',    am_index),
0x68: # LSL ,r
    ('',   'LSL\t{}',    am_index),
0x69: # ROL ,r
    ('',   'ROL\t{}',    am_index),
0x6a: # DEC ,r
    ('',   'DEC\t{}',    am_index),
0x6c: # INC ,r
    ('',   'INC\t{}',    am_index),
0x6d: # TST ,r
    ('',   'TST\t{}',    am_index),
0x6e: # JMP ,r
    ('A',  'JMP\t{}',    am_index),
0x6f: # CLR ,r
    ('',   'CLR\t{}',    am_index),
0x70: # NEG >nn
    ('',   'NEG\t{}',    word),
0x73: # COM >nn
    ('',   'COM\t{}',    word),
0x74: # LSR >nn
    ('',   'LSR\t{}',    word),
0x76: # ROR >nn
    ('',   'ROR\t{}',    word),
0x77: # ASR >nn
    ('',   'ASR\t{}',    word),
0x78: # LSL >nn
    ('',   'LSL\t{}',    word),
0x79: # ROL >nn
    ('',   'ROL\t{}',    word),
0x7a: # DEC >nn
    ('',   'DEC\t{}',    word),
0x7c: # INC >nn
    ('',   'INC\t{}',    word),
0x7d: # TST >nn
    ('',   'TST\t{}',    word),
0x7e: # JMP >nn
    ('AB', 'JMP\t{}',    word),
0x7f: # CLR >nn
    ('',   'CLR\t{}',    word),
0x80: # SUBA #n
    ('',   'SUBA\t#{}',  byte),
0x81: # CMPA #n
    ('',   'CMPA\t#{}',  byte),
0x82: # SBCA #n
    ('',   'SBCA\t#{}',  byte),
0x83: # SUBD #nn
    ('',   'SUBD\t#{}',  word),
0x84: # ANDA #n
    ('',   'ANDA\t#{}',  byte),
0x85: # BITA #n
    ('',   'BITA\t#{}',  byte),
0x86: # LDA #n
    ('',   'LDA\t#{}',   byte),
0x88: # EORA #n
    ('',   'EORA\t#{}',  byte),
0x89: # ADCA #n
    ('',   'ADCA\t#{}',  byte),
0x8a: # ORA #n
    ('',   'ORA\t#{}',   byte),
0x8b: # ADDA #n
    ('',   'ADDA\t#{}',  byte),
0x8c: # CMPX #nn
    ('',   'CMPX\t#{}',  word),
0x8d: # BSR
    ('B',  'BSR\t{}',    am_relative),
0x8e: # LDX #nn
    ('',   'LDX\t#{}',   word),
0x90: # SUBA <n
    ('',   'SUBA\t<{}',  byte),
0x91: # CMPA <n
    ('',   'CMPA\t<{}',  byte),
0x92: # SBCA <n
    ('',   'SBCA\t<{}',  byte),
0x93: # SUBD <n
    ('',   'SUBD\t<{}',  byte),
0x94: # ANDA <n
    ('',   'ANDA\t<{}',  byte),
0x95: # BITA <n
    ('',   'BITA\t<{}',  byte),
0x96: # LDA <n
    ('',   'LDA\t<{}',   byte),
0x97: # STA <n
    ('',   'STA\t<{}',   byte),
0x98: # EORA <n
    ('',   'EORA\t<{}',  byte),
0x99: # ADCA <n
    ('',   'ADCA\t<{}',  byte),
0x9a: # ORA <n
    ('',   'ORA\t<{}',   byte),
0x9b: # ADDA <n
    ('',   'ADDA\t<{}',  byte),
0x9c: # CMPX <n
    ('',   'CMPX\t<{}',  byte),
0x9d: # JSR <n
    ('',   'JSR\t<{}',   byte),
0x9e: # LDX <n
    ('',   'LDX\t<{}',   byte),
0x9f: # STX <n
    ('',   'STX\t<{}',   byte),
0xa0: # SUBA ,r
    ('',   'SUBA\t{}',   am_index),
0xa1: # CMPA ,r
    ('',   'CMPA\t{}',   am_index),
0xa2: # SBCA ,r
    ('',   'SBCA\t{}',   am_index),
0xa3: # SUBD ,r
    ('',   'SUBD\t{}',   am_index),
0xa4: # ANDA ,r
    ('',   'ANDA\t{}',   am_index),
0xa5: # BITA ,r
    ('',   'BITA\t{}',   am_index),
0xa6: # LDA ,r
    ('',   'LDA\t{}',    am_index),
0xa7: # STA ,r
    ('',   'STA\t{}',    am_index),
0xa8: # EORA ,r
    ('',   'EORA\t{}',   am_index),
0xa9: # ADCA ,r
    ('',   'ADCA\t{}',   am_index),
0xaa: # ORA ,r
    ('',   'ORA\t{}',    am_index),
0xab: # ADDA ,r
    ('',   'ADDA\t{}',   am_index),
0xac: # CMPX ,r
    ('',   'CMPX\t{}',   am_index),
0xad: # JSR ,r
    ('',   'JSR\t{}',    am_index),
0xae: # LDX ,r
    ('',   'LDX\t{}',    am_index),
0xaf: # STX ,r
    ('',   'STX\t{}',    am_index),
0xb0: # SUBA >nn
    ('',   'SUBA\t{}',   word),
0xb1: # CMPA >nn
    ('',   'CMPA\t{}',   word),
0xb2: # SBCA >nn
    ('',   'SBCA\t{}',   word),
0xb3: # SUBD >nn
    ('',   'SUBD\t{}',   word),
0xb4: # ANDA >nn
    ('',   'ANDA\t{}',   word),
0xb5: # BITA >nn
    ('',   'BITA\t{}',   word),
0xb6: # LDA >nn
    ('',   'LDA\t{}',    word),
0xb7: # STA >nn
    ('',   'STA\t{}',    word),
0xb8: # EORA >nn
    ('',   'EORA\t{}',   word),
0xb9: # ADCA >nn
    ('',   'ADCA\t{}',   word),
0xba: # ORA >nn
    ('',   'ORA\t{}',    word),
0xbb: # ADDA >nn
    ('',   'ADDA\t{}',   word),
0xbc: # CMPX >nn
    ('',   'CMPX\t{}',   word),
0xbd: # JSR >nn
    ('B',  'JSR\t{}',    word),
0xbe: # LDX >nn
    ('',   'LDX\t{}',    word),
0xbf: # STX >nn
    ('',   'STX\t{}',    word),
0xc0: # SUBB #n
    ('',   'SUBB\t#{}',  byte),
0xc1: # CMPB #n
    ('',   'CMPB\t#{}',  byte),
0xc2: # SBCB #n
    ('',   'SBCB\t#{}',  byte),
0xc3: # ADDD #nn
    ('',   'ADDD\t#{}',  word),
0xc4: # ANDB #n
    ('',   'ANDB\t#{}',  byte),
0xc5: # BITB #n
    ('',   'BITB\t#{}',  byte),
0xc6: # LDB #n
    ('',   'LDB\t#{}',   byte),
0xc8: # EORB #n
    ('',   'EORB\t#{}',  byte),
0xc9: # ADCB #n
    ('',   'ADCB\t#{}',  byte),
0xca: # ORB #n
    ('',   'ORB\t#{}',   byte),
0xcb: # ADDB #n
    ('',   'ADDB\t#{}',  byte),
0xcc: # LDD #nn
    ('',   'LDD\t#{}',   word),
0xce: # LDU #nn
    ('',   'LDU\t#{}',   word),
0xd0: # SUBB <n
    ('',   'SUBB\t<{}',  byte),
0xd1: # CMPB <n
    ('',   'CMPB\t<{}',  byte),
0xd2: # SBCB <n
    ('',   'SBCB\t<{}',  byte),
0xd3: # ADDD <n
    ('',   'ADDD\t<{}',  byte),
0xd4: # ANDB <n
    ('',   'ANDB\t<{}',  byte),
0xd5: # BITB <n
    ('',   'BITB\t<{}',  byte),
0xd6: # LDB <n
    ('',   'LDB\t<{}',   byte),
0xd7: # STB <n
    ('',   'STB\t<{}',   byte),
0xd8: # EORB <n
    ('',   'EORB\t<{}',  byte),
0xd9: # ADCB <n
    ('',   'ADCB\t<{}',  byte),
0xda: # ORB <n
    ('',   'ORB\t<{}',   byte),
0xdb: # ADDB <n
    ('',   'ADDB\t<{}',  byte),
0xdc: # LDD <n
    ('',   'LDD\t<{}',   byte),
0xdd: # STD <n
    ('',   'STD\t<{}',   byte),
0xde: # LDU <n
    ('',   'LDU\t<{}',   byte),
0xdf: # STU <n
    ('',   'STU\t<{}',   byte),
0xe0: # SUBB ,r
    ('',   'SUBB\t{}',   am_index),
0xe1: # CMPB ,r
    ('',   'CMPB\t{}',   am_index),
0xe2: # SBCB ,r
    ('',   'SBCB\t{}',   am_index),
0xe3: # ADDD ,r
    ('',   'ADDD\t{}',   am_index),
0xe4: # ANDB ,r
    ('',   'ANDB\t{}',   am_index),
0xe5: # BITB ,r
    ('',   'BITB\t{}',   am_index),
0xe6: # LDB ,r
    ('',   'LDB\t{}',    am_index),
0xe7: # STB ,r
    ('',   'STB\t{}',    am_index),
0xe8: # EORB ,r
    ('',   'EORB\t{}',   am_index),
0xe9: # ADCB ,r
    ('',   'ADCB\t{}',   am_index),
0xea: # ORB ,r
    ('',   'ORB\t{}',    am_index),
0xeb: # ADDB ,r
    ('',   'ADDB\t{}',   am_index),
0xec: # LDD ,r
    ('',   'LDD\t{}',    am_index),
0xed: # STD ,r
    ('',   'STD\t{}',    am_index),
0xee: # LDU ,r
    ('',   'LDU\t{}',    am_index),
0xef: # STU ,r
    ('',   'STU\t{}',    am_index),
0xf0: # SUBB >nn
    ('',   'SUBB\t{}',   word),
0xf1: # CMPB >nn
    ('',   'CMPB\t{}',   word),
0xf2: # SBCB >nn
    ('',   'SBCB\t{}',   word),
0xf3: # ADDD >nn
    ('',   'ADDD\t{}',   word),
0xf4: # ANDB >nn
    ('',   'ANDB\t{}',   word),
0xf5: # BITB >nn
    ('',   'BITB\t{}',   word),
0xf6: # LDB >nn
    ('',   'LDB\t{}',    word),
0xf7: # STB >nn
    ('',   'STB\t{}',    word),
0xf8: # EORB >nn
    ('',   'EORB\t{}',   word),
0xf9: # ADCB >nn
    ('',   'ADCB\t{}',   word),
0xfa: # ORB >nn
    ('',   'ORB\t{}',    word),
0xfb: # ADDB >nn
    ('',   'ADDB\t{}',   word),
0xfc: # LDD >nn
    ('',   'LDD\t{}',    word),
0xfd: # STD >nn
    ('',   'STD\t{}',    word),
0xfe: # LDU >nn
    ('',   'LDU\t{}',    word),
0xff: # STU >nn
    ('',   'STU\t{}',    word),
}

def op():
    global flags, table
    opcode = fetch()
    if opcode not in table:
        flags = ''
        return ''
    t = table[opcode]
    flags = t[0]
    operands = [f() for f in t[2:]]
    return t[1].lower().format(*operands) if '' not in operands else ''

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
            size = int(words[2]) if len(words) > 2 else 1
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
            size = int(words[2]) if len(words) > 2 else 1
            string[base:base + size] = [True] * size
        elif words[0] == 't':
            base = int(words[1], 16)
            for index in range(int(words[2]) if len(words) > 2 else 1):
                pointer[base + index * 2] = True
                jumplabel[buffer[base + index * 2] << 8 | buffer[base + index * 2 + 1]] = True
            noentry = False
        elif words[0] == 'u':
            base = int(words[1], 16)
            for index in range(int(words[2]) if len(words) > 2 else 1):
                pointer[base + index * 2] = True
                label[buffer[base + index * 2] << 8 | buffer[base + index * 2 + 1]] = True
        elif words[0] == 'v':
            base = int(words[1], 16)
            for index in range(int(words[2]) if len(words) > 2 else 1):
                pointer[base + index * 3] = True
                label[buffer[base + index * 3] << 8 | buffer[base + index * 3 + 1]] = True

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
    print(f'\t\t\t************************************************', file=file)
    print(f'\t\t\t*\tMC6809 disassembler', file=file)
    print(f'\t\t\t*\tfilename: {args[0]}', file=file)
    print(f'\t\t\t************************************************', file=file)
    print(f'\t\t\t\torg\t${start:0=4x}', file=file)
    print(f'\t\t\t', file=file)
else:
    print(f'************************************************', file=file)
    print(f'*\tMC6809 disassembler', file=file)
    print(f'*\tfilename: {args[0]}', file=file)
    print(f'************************************************', file=file)
    print(f'\torg\t${start:0=4x}', file=file)
    print(f'', file=file)
location = start
while location < end:
    base = location
    if base in remark:
        for s in remark[base]:
            if listing:
                print(f'{base:0=4X}\t\t\t', end='', file=file)
            print(f'*{s}', file=file)
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
            print(f'L{base:0=4x}', end='', file=file)
        print('\t' + s, file=file)
    elif string[base]:
        if listing:
            print(f'{base:0=4X}\t\t\t', end='', file=file)
        if label[base]:
            print(f'L{base:0=4x}', end='', file=file)
        location = base
        print(f'\tfcc\t\'{fetch():c}', end='', file=file)
        while location < end and string[location] and not label[location]:
            print(f'{fetch():c}', end='', file=file)
        print('\'', file=file)
    elif bytestring[base]:
        if listing:
            print(f'{base:0=4X}\t\t\t', end='', file=file)
        if label[base]:
            print(f'L{base:0=4x}', end='', file=file)
        location = base
        print(f'\tfcb\t${fetch():0=2x}', end='', file=file)
        for i in range(7):
            if location >= end or not bytestring[location] or label[location]:
                break
            print(f',${fetch():0=2x}', end='', file=file)
        print('', file=file)
    elif pointer[base]:
        if listing:
            print(f'{base:0=4X}\t\t\t', end='', file=file)
        if label[base]:
            print(f'L{base:0=4x}', end='', file=file)
        location = base
        print(f'\tfdb\tL{fetch() << 8 | fetch():0=4x}', end='', file=file)
        for i in range(3):
            if location >= end or not pointer[location] or label[location]:
                break
            print(f',L{fetch() << 8 | fetch():0=4x}', end='', file=file)
        print('', file=file)
    else:
        location = base
        for i in range(size):
            base = location
            c = fetch()
            if listing:
                print(f'{base:0=4X}  {c:0=2X}\t\t', end='', file=file)
            if label[base] or jumplabel[base]:
                print(f'L{base:0=4x}', end='', file=file)
            print(f'\tfcb\t${c:0=2x}', end='', file=file)
            if c >= 0x20 and c < 0x7f:
                print(f'\t\'{c:c}\'', end='', file=file)
            print('', file=file)
if listing:
    print(f'{location & 0xffff:0=4X}\t\t\t', end='', file=file)
print('\tend', file=file)
