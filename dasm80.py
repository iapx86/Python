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
    return f'{operand:0{2 + (operand >= 0xa0)}x}h'

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
    return f'L{operand:04x}'

def relative():
    global jumplabel, label, location, flags
    operand = (lambda x : x & 0x7f | -(x & 0x80))(fetch()) + location & 0xffff
    jumplabel[operand] = True
    return f'L{operand:04x}'

table_fdcb = {}

for i, op in {0x00:'RLC', 0x08:'RRC', 0x10:'RL', 0x18:'RR', 0x20:'SLA', 0x28:'SRA', 0x38:'SRL'}.items():
    table_fdcb[i | 6] = (f'{op} (IY+d)', '', f'{op}\t(IY''{})')
for i, op, b, in [(i | b << 3, op, b) for i, op in {0x40:'BIT', 0x80:'RES', 0xc0:'SET'}.items() for b in range(8)]:
    table_fdcb[i | 6] = (f'{op} {b},(IY+d)', '', f'{op}\t{b},(IY''{})')

def op_fdcb():
    global table_fdcb
    d = sbyte()
    opcode = fetch()
    if opcode not in table_fdcb:
        return ''
    return table_fdcb[opcode][2].lower().format(d)

table_ddcb = {}

for i, op in {0x00:'RLC', 0x08:'RRC', 0x10:'RL', 0x18:'RR', 0x20:'SLA', 0x28:'SRA', 0x38:'SRL'}.items():
    table_ddcb[i | 6] = (f'{op} (IX+d)', '', f'{op}\t(IX''{})')
for i, op, b, in [(i | b << 3, op, b) for i, op in {0x40:'BIT', 0x80:'RES', 0xc0:'SET'}.items() for b in range(8)]:
    table_ddcb[i | 6] = (f'{op} {b},(IX+d)', '', f'{op}\t{b},(IX''{})')

def op_ddcb():
    global table_ddcb
    d = sbyte()
    opcode = fetch()
    if opcode not in table_ddcb:
        return ''
    return table_ddcb[opcode][2].lower().format(d)

table_fd = {
    0x09: ('ADD IY,BC',    '',   'ADD\tIY,BC'),
    0x19: ('ADD IY,DE',    '',   'ADD\tIY,DE'),
    0x21: ('LD IY,nn',     '',   'LD\tIY,{}',     word),
    0x22: ('LD (nn),IY',   '',   'LD\t({}),IY',   word),
    0x23: ('INC IY',       '',   'INC\tIY'),
    0x24: ('INC IYH',      '',   'INC\tIYH'), # undefined operation
    0x25: ('DEC IYH',      '',   'DEC\tIYH'), # undefined operation
    0x26: ('LD IYH,n',     '',   'LD\tIYH,{}',    byte), # undefined operation
    0x29: ('ADD IY,IY',    '',   'ADD\tIY,IY'),
    0x2a: ('LD IY,(nn)',   '',   'LD\tIY,({})',   word),
    0x2b: ('DEC IY',       '',   'DEC\tIY'),
    0x2c: ('INC IYL',      '',   'INC\tIYL'), # undefined operation
    0x2d: ('DEC IYL',      '',   'DEC\tIYL'), # undefined operation
    0x2e: ('LD IYL,n',     '',   'LD\tIYL,{}',    byte), # undefined operation
    0x34: ('INC (IY+d)',   '',   'INC\t(IY{})',   sbyte),
    0x35: ('DEC (IY+d)',   '',   'DEC\t(IY{})',   sbyte),
    0x36: ('LD (IY+d),n',  '',   'LD\t(IY{}),{}', sbyte, byte),
    0x39: ('ADD IY,SP',    '',   'ADD\tIY,SP'),
    0x84: ('ADD A,IYH',    '',   'ADD\tA,IYH'), # undefined operation
    0x85: ('ADD A,IYL',    '',   'ADD\tA,IYL'), # undefined operation
    0x86: ('ADD A,(IY+d)', '',   'ADD\tA,(IY{})', sbyte),
    0x8c: ('ADC A,IYH',    '',   'ADC\tA,IYH'), # undefined operation
    0x8d: ('ADC A,IYL',    '',   'ADC\tA,IYL'), # undefined operation
    0x8e: ('ADC A,(IY+d)', '',   'ADC\tA,(IY{})', sbyte),
    0x94: ('SUB IYH',      '',   'SUB\tIYH'), # undefined operation
    0x95: ('SUB IYL',      '',   'SUB\tIYL'), # undefined operation
    0x96: ('SUB (IY+d)',   '',   'SUB\t(IY{})',   sbyte),
    0x9c: ('SBC A,IYH',    '',   'SBC\tA,IYH'), # undefined operation
    0x9d: ('SBC A,IYL',    '',   'SBC\tA,IYL'), # undefined operation
    0x9e: ('SBC A,(IY+d)', '',   'SBC\tA,(IY{})', sbyte),
    0xa4: ('AND IYH',      '',   'AND\tIYH'), # undefined operation
    0xa5: ('AND IYL',      '',   'AND\tIYL'), # undefined operation
    0xa6: ('AND (IY+d)',   '',   'AND\t(IY{})',   sbyte),
    0xac: ('XOR IYH',      '',   'XOR\tIYH'), # undefined operation
    0xad: ('XOR IYL',      '',   'XOR\tIYL'), # undefined operation
    0xae: ('XOR (IY+d)',   '',   'XOR\t(IY{})',   sbyte),
    0xb4: ('OR IYH',       '',   'OR\tIYH'), # undefined operation
    0xb5: ('OR IYL',       '',   'OR\tIYL'), # undefined operation
    0xb6: ('OR (IY+d)',    '',   'OR\t(IY{})',    sbyte),
    0xbc: ('CP IYH',       '',   'CP\tIYH'), # undefined operation
    0xbd: ('CP IYL',       '',   'CP\tIYL'), # undefined operation
    0xbe: ('CP (IY+d)',    '',   'CP\t(IY{})',    sbyte),
    0xcb: ('',             '',   '{}',            op_fdcb),
    0xe1: ('POP IY',       '',   'POP\tIY'),
    0xe3: ('EX (SP),IY',   '',   'EX\t(SP),IY'),
    0xe5: ('PUSH IY',      '',   'PUSH\tIY'),
    0xe9: ('JP (IY)',      'A',  'JP\t(IY)'),
    0xf9: ('LD SP,IY',     '',   'LD\tSP,IY'),
}

for i, r in {0:'B', 1:'C', 2:'D', 3:'E', 4:'H', 5:'L', 7:'A'}.items():
    table_fd[0x46 | i << 3] = (f'LD {r},(IY+d)', '', f'LD\t{r},(IY''{})', sbyte)
    table_fd[0x70 | i] = (f'LD (IY+d),{r}', '', 'LD\t(IY{}),'f'{r}', sbyte)
for i, r in {0:'B', 1:'C', 2:'D', 3:'E', 7:'A'}.items():
    table_fd[0x44 | i << 3] = (f'LD {r},IYH', '', f'LD\t{r},IYH') # undefined operation
    table_fd[0x45 | i << 3] = (f'LD {r},IYL', '', f'LD\t{r},IYL') # undefined operation
    table_fd[0x60 | i] = (f'LD IYH,{r}', '', f'LD\tIYH,{r}') # undefined operation
    table_fd[0x68 | i] = (f'LD IYL,{r}', '', f'LD\tIYL,{r}') # undefined operation

def op_fd():
    global flags, table_fd
    opcode = fetch()
    if opcode not in table_fd:
        return ''
    t = table_fd[opcode]
    flags = t[1]
    return t[2].lower().format(*[f() for f in t[3:]])

table_ed = {
    0x44: ('NEG',    '',   'NEG'),
    0x45: ('RETN',   'A',  'RETN'),
    0x46: ('IM 0',   '',   'IM\t0'),
    0x47: ('LD I,A', '',   'LD\tI,A'),
    0x4d: ('RETI',   'A',  'RETI'),
    0x4f: ('LD R,A', '',   'LD\tR,A'),
    0x56: ('IM 1',   '',   'IM\t1'),
    0x57: ('LD A,I', '',   'LD\tA,I'),
    0x5e: ('IM 2',   '',   'IM\t2'),
    0x5f: ('LD A,R', '',   'LD\tA,R'),
    0x67: ('RRD',    '',   'RRD'),
    0x6f: ('RLD',    '',   'RLD'),
    0xa0: ('LDI',    '',   'LDI'),
    0xa1: ('CPI',    '',   'CPI'),
    0xa2: ('INI',    '',   'INI'),
    0xa3: ('OUTI',   '',   'OUTI'),
    0xa8: ('LDD',    '',   'LDD'),
    0xa9: ('CPD',    '',   'CPD'),
    0xaa: ('IND',    '',   'IND'),
    0xab: ('OUTD',   '',   'OUTD'),
    0xb0: ('LDIR',   '',   'LDIR'),
    0xb1: ('CPIR',   '',   'CPIR'),
    0xb2: ('INIR',   '',   'INIR'),
    0xb3: ('OTIR',   '',   'OTIR'),
    0xb8: ('LDDR',   '',   'LDDR'),
    0xb9: ('CPDR',   '',   'CPDR'),
    0xba: ('INDR',   '',   'INDR'),
    0xbb: ('OTDR',   '',   'OTDR'),
}

for i, r in {0:'B', 1:'C', 2:'D', 3:'E', 4:'H', 5:'L', 7:'A'}.items():
    table_ed[0x40 | i << 3] = (f'IN {r},(C)', '', f'IN\t{r},(C)')
    table_ed[0x41 | i << 3] = (f'OUT (C),{r}', '', f'OUT\t(C),{r}')
for i, rr in enumerate(('BC', 'DE', 'HL', 'SP')):
    table_ed[0x42 | i << 4] = (f'SBC HL,{rr}', '', f'SBC\tHL,{rr}')
    table_ed[0x4a | i << 4] = (f'ADC HL,{rr}', '', f'ADC\tHL,{rr}')
for i, rr in {0:'BC', 1:'DE', 3:'SP'}.items():
    table_ed[0x43 | i << 4] = (f'LD (nn),{rr}', '', 'LD\t({}),'f'{rr}', word)
    table_ed[0x4b | i << 4] = (f'LD {rr},(nn)', '', f'LD\t{rr},''({})', word)

def op_ed():
    global flags, table_ed
    opcode = fetch()
    if opcode not in table_ed:
        return ''
    t = table_ed[opcode]
    flags = t[1]
    return t[2].lower().format(*[f() for f in t[3:]])

table_dd = {
    0x09: ('ADD IX,BC',    '',   'ADD\tIX,BC'),
    0x19: ('ADD IX,DE',    '',   'ADD\tIX,DE'),
    0x21: ('LD IX,nn',     '',   'LD\tIX,{}',      word),
    0x22: ('LD (nn),IX',   '',   'LD\t({}),IX',    word),
    0x23: ('INC IX',       '',   'INC\tIX'),
    0x24: ('INC IXH',      '',   'INC\tIXH'), # undefined operation
    0x25: ('DEC IXH',      '',   'DEC\tIXH'), # undefined operation
    0x26: ('LD IXH,n',     '',   'LD\tIXH,{}',    byte), # undefined operation
    0x29: ('ADD IX,IX',    '',   'ADD\tIX,IX'),
    0x2a: ('LD IX,(nn)',   '',   'LD\tIX,({})',   word),
    0x2b: ('DEC IX',       '',   'DEC\tIX'),
    0x2c: ('INC IXL',      '',   'INC\tIXL'), # undefined operation
    0x2d: ('DEC IXL',      '',   'DEC\tIXL'), # undefined operation
    0x2e: ('LD IXL,n',     '',   'LD\tIXL,{}',    byte), # undefined operation
    0x34: ('INC (IX+d)',   '',   'INC\t(IX{})',   sbyte),
    0x35: ('DEC (IX+d)',   '',   'DEC\t(IX{})',   sbyte),
    0x36: ('LD (IX+d),n',  '',   'LD\t(IX{}),{}', sbyte, byte),
    0x39: ('ADD IX,SP',    '',   'ADD\tIX,SP'),
    0x84: ('ADD A,IXH',    '',   'ADD\tA,IXH'), # undefined operation
    0x85: ('ADD A,IXL',    '',   'ADD\tA,IXL'), # undefined operation
    0x86: ('ADD A,(IX+d)', '',   'ADD\tA,(IX{})', sbyte),
    0x8c: ('ADC A,IXH',    '',   'ADC\tA,IXH'), # undefined operation
    0x8d: ('ADC A,IXL',    '',   'ADC\tA,IXL'), # undefined operation
    0x8e: ('ADC A,(IX+d)', '',   'ADC\tA,(IX{})', sbyte),
    0x94: ('SUB IXH',      '',   'SUB\tIXH'), # undefined operation
    0x95: ('SUB IXL',      '',   'SUB\tIXL'), # undefined operation
    0x96: ('SUB (IX+d)',   '',   'SUB\t(IX{})',   sbyte),
    0x9c: ('SBC A,IXH',    '',   'SBC\tA,IXH'), # undefined operation
    0x9d: ('SBC A,IXL',    '',   'SBC\tA,IXL'), # undefined operation
    0x9e: ('SBC A,(IX+d)', '',   'SBC\tA,(IX{})', sbyte),
    0xa4: ('AND IXH',      '',   'AND\tIXH'), # undefined operation
    0xa5: ('AND IXL',      '',   'AND\tIXL'), # undefined operation
    0xa6: ('AND (IX+d)',   '',   'AND\t(IX{})',   sbyte),
    0xac: ('XOR IXH',      '',   'XOR\tIXH'), # undefined operation
    0xad: ('XOR IXL',      '',   'XOR\tIXL'), # undefined operation
    0xae: ('XOR (IX+d)',   '',   'XOR\t(IX{})',   sbyte),
    0xb4: ('OR IXH',       '',   'OR\tIXH'), # undefined operation
    0xb5: ('OR IXL',       '',   'OR\tIXL'), # undefined operation
    0xb6: ('OR (IX+d)',    '',   'OR\t(IX{})',    sbyte),
    0xbc: ('CP IXH',       '',   'CP\tIXH'), # undefined operation
    0xbd: ('CP IXL',       '',   'CP\tIXL'), # undefined operation
    0xbe: ('CP (IX+d)',    '',   'CP\t(IX{})',    sbyte),
    0xcb: ('',             '',   '{}',            op_ddcb),
    0xe1: ('POP IX',       '',   'POP\tIX'),
    0xe3: ('EX (SP),IX',   '',   'EX\t(SP),IX'),
    0xe5: ('PUSH IX',      '',   'PUSH\tIX'),
    0xe9: ('JP (IX)',      'A',  'JP\t(IX)'),
    0xf9: ('LD SP,IX',     '',   'LD\tSP,IX'),
}

for i, r in {0:'B', 1:'C', 2:'D', 3:'E', 4:'H', 5:'L', 7:'A'}.items():
    table_dd[0x46 | i << 3] = (f'LD {r},(IX+d)', '', f'LD\t{r},(IX''{})', sbyte)
    table_dd[0x70 | i] = (f'LD (IX+d),{r}', '', 'LD\t(IX{}),'f'{r}', sbyte)
for i, r in {0:'B', 1:'C', 2:'D', 3:'E', 7:'A'}.items():
    table_dd[0x44 | i << 3] = (f'LD {r},IXH', '', f'LD\t{r},IXH') # undefined operation
    table_dd[0x45 | i << 3] = (f'LD {r},IXL', '', f'LD\t{r},IXL') # undefined operation
    table_dd[0x60 | i] = (f'LD IXH,{r}', '', f'LD\tIXH,{r}') # undefined operation
    table_dd[0x68 | i] = (f'LD IXL,{r}', '', f'LD\tIXL,{r}') # undefined operation

def op_dd():
    global flags, table_dd
    opcode = fetch()
    if opcode not in table_dd:
        return ''
    t = table_dd[opcode]
    flags = t[1]
    return t[2].lower().format(*[f() for f in t[3:]])

table_cb = {}

for i, op in {0x00:'RLC', 0x08:'RRC', 0x10:'RL', 0x18:'RR', 0x20:'SLA', 0x28:'SRA', 0x38:'SRL'}.items():
    for j, r in enumerate(('B', 'C', 'D', 'E', 'H', 'L', '(HL)', 'A')):
        table_cb[i | j] = (f'{op} {r}', '', f'{op}\t{r}')
for i, op, b, in [(i | b << 3, op, b) for i, op in {0x40:'BIT', 0x80:'RES', 0xc0:'SET'}.items() for b in range(8)]:
    for j, r in enumerate(('B', 'C', 'D', 'E', 'H', 'L', '(HL)', 'A')):
        table_cb[i | j] = (f'{op} {b},{r}', '', f'{op}\t{b},{r}')

def op_cb():
    global table_cb
    opcode = fetch()
    if opcode not in table_cb:
        return ''
    return table_cb[opcode][2].lower()

table = {
    0x00: ('NOP',        '',   'NOP'),
    0x02: ('LD (BC),A',  '',   'LD\t(BC),A'),
    0x07: ('RLCA',       '',   'RLCA'),
    0x08: ('EX AF,AF\'', '',   'EX\tAF,AF\''),
    0x0a: ('LD A,(BC)',  '',   'LD\tA,(BC)'),
    0x0f: ('RRCA',       '',   'RRCA'),
    0x10: ('DJNZ e',     'B',  'DJNZ\t{}',    relative),
    0x12: ('LD (DE),A',  '',   'LD\t(DE),A'),
    0x17: ('RLA',        '',   'RLA'),
    0x18: ('JR e',       'AB', 'JR\t{}',      relative),
    0x1a: ('LD A,(DE)',  '',   'LD\tA,(DE)'),
    0x1f: ('RRA',        '',   'RRA'),
    0x20: ('JR NZ,e',    'B',  'JR\tNZ,{}',   relative),
    0x22: ('LD (nn),HL', '',   'LD\t({}),HL', word),
    0x27: ('DAA',        '',   'DAA'),
    0x28: ('JR Z,e',     'B',  'JR\tZ,{}',    relative),
    0x2a: ('LD HL,(nn)', '',   'LD\tHL,({})', word),
    0x2f: ('CPL',        '',   'CPL'),
    0x30: ('JR NC,e',    'B',  'JR\tNC,{}',   relative),
    0x32: ('LD (nn),A',  '',   'LD\t({}),A',  word),
    0x37: ('SCF',        '',   'SCF'),
    0x38: ('JR C,e',     'B',  'JR\tC,{}',    relative),
    0x3a: ('LD A,(nn)',  '',   'LD\tA,({})',  word),
    0x3f: ('CCF',        '',   'CCF'),
    0x76: ('HALT',       '',   'HALT'),
    0xc3: ('JP nn',      'AB', 'JP\t{}',      word),
    0xc6: ('ADD A,n',    '',   'ADD\tA,{}',   byte),
    0xc9: ('RET',        'A',  'RET'),
    0xcb: ('',           '',   '{}',          op_cb),
    0xcd: ('CALL nn',    'B',  'CALL\t{}',    word),
    0xce: ('ADC A,n',    '',   'ADC\tA,{}',   byte),
    0xd3: ('OUT n,A',    'B',  'OUT\t{},A',   byte),
    0xd6: ('SUB n',      '',   'SUB\t{}',     byte),
    0xd9: ('EXX',        '',   'EXX'),
    0xdb: ('IN A,n',     '',   'IN\tA,{}',    byte),
    0xdd: ('',           '',   '{}',          op_dd),
    0xde: ('SBC A,n',    '',   'SBC\tA,{}',   byte),
    0xe3: ('EX (SP),HL', '',   'EX\t(SP),HL'),
    0xe6: ('AND n',      '',   'AND\t{}',     byte),
    0xe9: ('JP (HL)',    'A',  'JP\t(HL)'),
    0xeb: ('EX DE,HL',   '',   'EX\tDE,HL'),
    0xed: ('',           '',   '{}',          op_ed),
    0xee: ('XOR n',      '',   'XOR\t{}',     byte),
    0xf3: ('DI',         '',   'DI'),
    0xf6: ('OR n',       '',   'OR\t{}',      byte),
    0xf9: ('LD SP,HL',   '',   'LD\tSP,HL'),
    0xfb: ('EI',         '',   'EI'),
    0xfd: ('',           '',   '{}',          op_fd),
    0xfe: ('CP n',       '',   'CP\t{}',      byte),
}

for i, rr in enumerate(('BC', 'DE', 'HL', 'SP')):
    table[0x01 | i << 4] = (f'LD {rr},nn', '', f'LD\t{rr},''{}', word)
    table[0x03 | i << 4] = (f'INC {rr}', '', f'INC\t{rr}')
    table[0x09 | i << 4] = (f'ADD HL,{rr}', '', f'ADD\tHL,{rr}')
    table[0x0b | i << 4] = (f'DEC {rr}', '', f'DEC\t{rr}')
for i, r in enumerate(('B', 'C', 'D', 'E', 'H', 'L', '(HL)', 'A')):
    table[0x04 | i << 3] = (f'INC {r}', '', f'INC\t{r}')
    table[0x05 | i << 3] = (f'DEC {r}', '', f'DEC\t{r}')
    table[0x06 | i << 3] = (f'LD {r},n', '', f'LD\t{r},''{}', byte)
    table[0x80 | i] = (f'ADD A,{r}', '', f'ADD\tA,{r}')
    table[0x88 | i] = (f'ADC A,{r}', '', f'ADC\tA,{r}')
    table[0x90 | i] = (f'SUB {r}', '', f'SUB\t{r}')
    table[0x98 | i] = (f'SBC A,{r}', '', f'SBC\tA,{r}')
    table[0xa0 | i] = (f'AND {r}', '', f'AND\t{r}')
    table[0xa8 | i] = (f'XOR {r}', '', f'XOR\t{r}')
    table[0xb0 | i] = (f'OR {r}', '', f'OR\t{r}')
    table[0xb8 | i] = (f'CP {r}', '', f'CP\t{r}')
for i, (r, s) in enumerate([(r, s) for r in ('B', 'C', 'D', 'E', 'H', 'L', '(HL)', 'A') for s in ('B', 'C', 'D', 'E', 'H', 'L', '(HL)', 'A')]):
    if r != '(HL)' or s != '(HL)':
        table[0x40 | i] = (f'LD {r},{s}', '', f'LD\t{r},{s}')
for i, cc in enumerate(('NZ', 'Z', 'NC', 'C', 'PO', 'PE', 'P', 'M')):
    table[0xc0 | i << 3] = (f'RET {cc}', '', f'RET\t{cc}')
    table[0xc2 | i << 3] = (f'JP {cc},nn', 'B', f'JP\t{cc},''{}', word)
    table[0xc4 | i << 3] = (f'CALL {cc},nn', 'B', f'CALL\t{cc},''{}', word)
for i, qq in enumerate(('BC', 'DE', 'HL', 'AF')):
    table[0xc1 | i << 4] = (f'POP {qq}', '', f'POP\t{qq}')
    table[0xc5 | i << 4] = (f'PUSH {qq}', '', f'PUSH\t{qq}')
for p in range(0, 0x40, 8):
    table[0xc7 | p] = (f'RST {p:02X}h', '', f'RST\t{p:02X}h')

def op():
    global flags, table
    opcode = fetch()
    if opcode not in table:
        flags = ''
        return ''
    t = table[opcode]
    flags = t[1]
    return t[2].lower().format(*[f() for f in t[3:]])

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
    end = min(start + len(data), 0x10000)
    buffer[start:end] = data
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
    print(f'\t\t\t\torg\t{start:0{4 + (start >= 0xa000)}x}h', file=file)
    print(f'\t\t\t', file=file)
else:
    print(f';-----------------------------------------------', file=file)
    print(f';\tZ80 disassembler', file=file)
    print(f';\tfilename: {args[0]}', file=file)
    print(f';-----------------------------------------------', file=file)
    print(f'\torg\t{start:0{4 + (start >= 0xa000)}x}h', file=file)
    print(f'', file=file)
location = start
while location < end:
    base = location
    if base in remark:
        for s in remark[base]:
            if listing:
                print(f'{base:04X}\t\t\t', end='', file=file)
            print(f';{s}', file=file)
    if code[base]:
        s = op()
        size = location - base
    else:
        s = ''
        size = 1
    if s != '':
        if listing:
            print(f'{base:04X} ', end='', file=file)
            location = base
            for i in range(size):
                print(f' {fetch():02X}', end='', file=file)
            print('\t\t' if size < 4 else '\t', end='', file=file)
        if jumplabel[base]:
            print(f'L{base:04x}:', end='', file=file)
        print('\t' + s, file=file)
    elif string[base]:
        if listing:
            print(f'{base:04X}\t\t\t', end='', file=file)
        if label[base]:
            print(f'L{base:04x}:', end='', file=file)
        location = base
        print(f'\tdb\t\'{fetch():c}', end='', file=file)
        while location < end and string[location] and not label[location]:
            print(f'{fetch():c}', end='', file=file)
        print('\'', file=file)
    elif bytestring[base]:
        if listing:
            print(f'{base:04X}\t\t\t', end='', file=file)
        if label[base]:
            print(f'L{base:04x}:', end='', file=file)
        location = base
        c = fetch()
        print(f'\tdb\t${c:0{2 + (c >= 0xa0)}x}', end='', file=file)
        for i in range(7):
            if location >= end or not bytestring[location] or label[location]:
                break
            c = fetch()
            print(f',{c:0{2 + (c >= 0xa0)}x}h', end='', file=file)
        print('', file=file)
    elif pointer[base]:
        if listing:
            print(f'{base:04X}\t\t\t', end='', file=file)
        if label[base]:
            print(f'L{base:04x}:', end='', file=file)
        location = base
        print(f'\tdw\tL{fetch() | fetch() << 8:04x}', end='', file=file)
        for i in range(3):
            if location >= end or not pointer[location] or label[location]:
                break
            print(f',L{fetch() | fetch() << 8:04x}', end='', file=file)
        print('', file=file)
    else:
        location = base
        for i in range(size):
            base = location
            c = fetch()
            if listing:
                print(f'{base:04X}  {c:02X}\t\t', end='', file=file)
            if label[base] or jumplabel[base]:
                print(f'L{base:04x}:', end='', file=file)
            print(f'\tdb\t{c:0{2 + (c >= 0xa0)}x}h', end='', file=file)
            if c >= 0x20 and c < 0x7f:
                print(f'\t;\'{c:c}\'', end='', file=file)
            print('', file=file)
if listing:
    print(f'{location & 0xffff:04X}\t\t\t', end='', file=file)
print('\tend', file=file)
