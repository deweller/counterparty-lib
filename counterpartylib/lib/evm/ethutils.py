try:
    from Crypto.Hash import keccak

    sha3_256 = lambda x: keccak.new(digest_bits=256, data=x).digest()
except:
    import sha3 as _sha3

    sha3_256 = lambda x: _sha3.sha3_256(x).digest()

import sys
import rlp
from rlp.sedes import big_endian_int, BigEndianInt, Binary
from rlp.utils import decode_hex, encode_hex, ascii_chr, str_to_bytes
import random
import math
import binascii

from counterpartylib.lib import util, script

big_endian_to_int = lambda x: big_endian_int.deserialize(str_to_bytes(x).lstrip(b'\x00'))
int_to_big_endian = lambda x: big_endian_int.serialize(x)

TT256 = 2 ** 256
TT256M1 = 2 ** 256 - 1
TT255 = 2 ** 255


is_numeric = lambda x: isinstance(x, int)
is_string = lambda x: isinstance(x, bytes)


def to_string(value):
    if isinstance(value, bytes):
        return value
    if isinstance(value, str):
        return bytes(value, 'utf-8')
    if isinstance(value, int):
        return bytes(str(value), 'utf-8')


def int_to_bytes(value):
    if isinstance(value, bytes):
        return value
    return int_to_big_endian(value)


def to_string_for_regexp(value):
    return str(to_string(value), 'utf-8')


unicode = str
isnumeric = is_numeric


def safe_ord(value):
    if isinstance(value, int):
        return value
    else:
        return ord(value)


# decorator


def debug(label):
    def deb(f):
        def inner(*args, **kwargs):
            i = random.randrange(1000000)
            print(label, i, 'start', args)
            x = f(*args, **kwargs)
            print(label, i, 'end', x)
            return x

        return inner

    return deb


def flatten(li):
    o = []
    for l in li:
        o.extend(l)
    return o


def bytearray_to_int(arr):
    o = 0
    for a in arr:
        o = (o << 8) + a
    return o


def int_to_32bytearray(i):
    o = [0] * 32
    for x in range(32):
        o[31 - x] = i & 0xff
        i >>= 8
    return o


def sha3(seed):
    return sha3_256(to_string(seed))


# @TODO
# assert sha3('') == 'c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470'

def add_checksum(x):
    if len(x) in (40, 48):
        x = decode_hex(x)
    if len(x) == 24:
        return x
    return x + sha3(x)[:4]


def check_and_strip_checksum(x):
    if len(x) in (40, 48):
        x = decode_hex(x)
    assert len(x) == 24 and sha3(x[:20])[:4] == x[-4:]
    return x[:20]


def normalize_address(x, allow_blank=False):
    if allow_blank and x == '':
        return ''
    if len(x) in (42, 50) and x[:2] == '0x':
        x = x[2:]
    if len(x) in (40, 48):
        x = decode_hex(x)
    if len(x) == 24:
        assert len(x) == 24 and sha3(x[:20])[:4] == x[-4:]
        x = x[:20]
    if len(x) != 20:
        raise Exception("Invalid address format: %r" % x)
    return x


def zpad(x, l):
    return b'\x00' * max(0, l - len(x)) + x


def zunpad(x):
    i = 0
    while i < len(x) and (x[i] == 0 or x[i] == '\x00'):
        i += 1
    return x[i:]


def int_to_addr(x):
    o = [''] * 20
    for i in range(20):
        o[19 - i] = ascii_chr(x & 0xff)
        x >>= 8
    return b''.join(o)


def coerce_addr_to_bin(x):
    if is_numeric(x):
        return encode_hex(zpad(big_endian_int.serialize(x), 20))
    elif len(x) == 40 or len(x) == 0:
        return decode_hex(x)
    else:
        return zpad(x, 20)[-20:]


def coerce_addr_to_hex(x):
    if is_numeric(x):
        return encode_hex(zpad(big_endian_int.serialize(x), 20))
    elif len(x) == 40 or len(x) == 0:
        return x
    else:
        return encode_hex(zpad(x, 20)[-20:])


def coerce_to_int(x):
    if is_numeric(x):
        return x
    elif len(x) == 40:
        return big_endian_to_int(decode_hex(x))
    else:
        return big_endian_to_int(x)


def coerce_to_bytes(x):
    if is_numeric(x):
        return big_endian_int.serialize(x)
    elif len(x) == 40:
        return decode_hex(x)
    else:
        return x


def parse_int_or_hex(s):
    if is_numeric(s):
        return s
    elif s[:2] in (b'0x', '0x'):
        s = to_string(s)
        tail = (b'0' if len(s) % 2 else b'') + s[2:]
        return big_endian_to_int(decode_hex(tail))
    else:
        return int(s)


def ceil32(x):
    return x if x % 32 == 0 else x + 32 - (x % 32)


def to_signed(i):
    return i if i < TT255 else i - TT256


def sha3rlp(x):
    return sha3(rlp.encode(x))


# Format encoders/decoders for bin, addr, int


def decode_bin(v):
    '''decodes a bytearray from serialization'''
    if not is_string(v):
        raise Exception("Value must be binary, not RLP array")
    return v


def decode_addr(v):
    '''decodes an address from serialization'''
    if len(v) not in [0, 20]:
        raise Exception("Serialized addresses must be empty or 20 bytes long!")
    return encode_hex(v)


def decode_int(v):
    '''decodes and integer from serialization'''
    if len(v) > 0 and (v[0] == '\x00' or v[0] == 0):
        raise Exception("No leading zero bytes allowed for integers")
    return big_endian_to_int(v)


def decode_int256(v):
    return big_endian_to_int(v)


def encode_bin(v):
    '''encodes a bytearray into serialization'''
    return v


def encode_root(v):
    '''encodes a trie root into serialization'''
    return v


def encode_int(v):
    '''encodes an integer into serialization'''
    if not is_numeric(v) or v < 0 or v >= TT256:
        raise Exception("Integer invalid or out of range: %r" % v)
    return int_to_big_endian(v)


def encode_int256(v):
    return zpad(int_to_big_endian(v), 256)


def scan_bin(v):
    if v[:2] in ('0x', b'0x'):
        return decode_hex(v[2:])
    else:
        return decode_hex(v)


def scan_int(v):
    if v[:2] in ('0x', b'0x'):
        return big_endian_to_int(decode_hex(v[2:]))
    else:
        return int(v)


def int_to_hex(x):
    o = encode_hex(encode_int(x))
    return '0x' + (o[1:] if (len(o) > 0 and o[0] == '0') else o)


def remove_0x_head(s):
    return s[2:] if s[:2] == b'0x' else s


def print_func_call(ignore_first_arg=False, max_call_number=100):
    ''' utility function to facilitate debug, it will print input args before
    function call, and print return value after function call

    usage:

        @print_func_call
        def some_func_to_be_debu():
            pass

    :param ignore_first_arg: whether print the first arg or not.
    useful when ignore the `self` parameter of an object method call
    '''
    from functools import wraps

    def display(x):
        x = to_string(x)
        try:
            x.decode('ascii')
        except:
            return 'NON_PRINTABLE'
        return x

    local = {'call_number': 0}

    def inner(f):

        @wraps(f)
        def wrapper(*args, **kwargs):
            local['call_number'] += 1
            tmp_args = args[1:] if ignore_first_arg and len(args) else args
            this_call_number = local['call_number']
            print(('{0}#{1} args: {2}, {3}'.format(
                f.__name__,
                this_call_number,
                ', '.join([display(x) for x in tmp_args]),
                ', '.join(display(key) + '=' + to_string(value)
                          for key, value in kwargs.items())
            )))
            res = f(*args, **kwargs)
            print(('{0}#{1} return: {2}'.format(
                f.__name__,
                this_call_number,
                display(res))))

            if local['call_number'] > 100:
                raise Exception("Touch max call number!")
            return res

        return wrapper

    return inner


def dump_state(trie):
    res = ''
    for k, v in list(trie.to_dict().items()):
        res += '%r:%r\n' % (encode_hex(k), encode_hex(v))
    return res


class Denoms():
    def __init__(self):
        self.wei = 1
        self.babbage = 10 ** 3
        self.lovelace = 10 ** 6
        self.shannon = 10 ** 9
        self.szabo = 10 ** 12
        self.finney = 10 ** 15
        self.ether = 10 ** 18
        self.turing = 2 ** 256


denoms = Denoms()

address = Binary.fixed_length(20, allow_empty=True)
int20 = BigEndianInt(20)
int32 = BigEndianInt(32)
int256 = BigEndianInt(256)
hash32 = Binary.fixed_length(32)
trie_root = Binary.fixed_length(32, allow_empty=True)


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[91m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def hexprint(x):
    assert type(x) in (bytes, list)
    if not x:
        return '<None>'
    if x != -1:
        return ('0x' + util.hexlify(bytes(x)))
    else:
        return 'OUT OF GAS'


'''
First byte of an encoded item

    x: single byte, itself
    |
    |
0x7f == 127

0x80 == 128
    |
    x: [0, 55] byte long string, x-0x80 == length
    |
0xb7 == 183

0xb8 == 184
    |
    x: [56, ] long string, x-0xf7 == length of the length
    |
0xbf == 191

0xc0 == 192
    |
    x: [0, 55] byte long list, x-0xc0 == length
    |
0xf7 == 247

0xf8 == 248
    |
    x: [56, ] long list, x-0xf7 == length of the length
    |
0xff == 255
'''


def decode_datalist(arr):
    if isinstance(arr, list):
        arr = ''.join(map(chr, arr))
    o = []
    for i in range(0, len(arr), 32):
        o.append(big_endian_to_int(arr[i:i + 32]))
    return o


def encode(input):
    if isinstance(input, bytes):
        if len(input) == 1 and ord(input) < 128:
            return input
        else:
            return encode_length(len(input), 128) + input
    elif isinstance(input, list):
        output = b''
        for item in input:
            output += encode(item)
        return encode_length(len(output), 192) + output


def encode_length(L, offset):
    if L < 56:
        return (L + offset).to_bytes(1, byteorder='big')
    elif L < 256 ** 8:
        BL = to_binary(L)
        return (len(BL) + offset + 55).to_bytes(1, byteorder='big') + BL
    else:
        raise Exception("input too long")


def to_binary(x):
    return b'' if x == 0 else to_binary(x // 256) + (x % 256).to_bytes(1, byteorder='big')