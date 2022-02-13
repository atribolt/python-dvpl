import os.path

import lz4
import lz4.block as lz4b
import sys
import math
import zlib
from logger import Logger


lz4_compression_low = 2
little_endian = 'little'
big_endian = 'big'
native_byteorder = sys.byteorder
invert_byteorder = big_endian if native_byteorder == little_endian else little_endian


def __int_to_native_byteorder(number: int) -> int:
  bytecount = math.ceil(number.bit_length() / 8)
  return int.from_bytes(number.to_bytes(bytecount, native_byteorder), invert_byteorder)


def __bytes_to_native_byteorder(data: bytes) -> bytes:
  return b''.join(reversed(data))


def __str_to_native_byteorder(string: str) -> str:
  return __bytes_to_native_byteorder(string.encode('utf-8')).decode('utf-8')


def __to_native_byteorder(data):
  converters = {
    int: __int_to_native_byteorder,
    str: __str_to_native_byteorder,
    bytes: __bytes_to_native_byteorder
  }

  return converters[type(data)](data)


def _to_byteorder(data, from_order):
  if sys.byteorder == from_order:
    return data
  else:
    return __to_native_byteorder(data)


class DvplData:
  _log = Logger('DvplData')
  no_compression = 0
  low_compression = 2

  class Sign:
    _log = Logger('DvplSign')

    def __init__(self):
      self.origin_size = 0
      self.compress_size = 0
      self.compress_hash_sum = 0
      self.compress_level = 0

    def load_from_dvpl(self, data):
      sign_len = 20

      if not type(data) is bytes:
        self._log.error(f'dvpl sign wont be load from ({type(data)}). expected (bytes)')
        return False, b''
      elif len(data) < sign_len:
        self._log.error(f'file lenght invalid')
        return False, b''

      sign = data[-20:]
      magic = _to_byteorder(sign[-4:], little_endian)
      if magic != b'DVPL':
        self._log.error(f'file is not dvpl')
        return False, b''

      self.origin_size = _to_byteorder(sign[0:4], little_endian)
      self.compress_size = _to_byteorder(sign[4:8], little_endian)
      self.compress_hash_sum = _to_byteorder(sign[8:12], little_endian).hex(' ')
      self.compress_level = _to_byteorder(sign[12:16], little_endian)

      self.origin_size = int.from_bytes(self.origin_size, little_endian)
      self.compress_size = int.from_bytes(self.compress_size, little_endian)
      self.compress_level = int.from_bytes(self.compress_level, little_endian)

      self._log.debug(f'Sign load: {self.origin_size} | {self.compress_size}')
      return True, data[:-20]

    @classmethod
    def create_from_data(cls, origin, compress):
      sign = DvplData.Sign()

      sign.origin_size = len(origin)
      sign.compress_size = len(compress)
      sign.compress_hash_sum = zlib.crc32(compress)
      if sign.origin_size > sign.compress_size:
        sign.compress_level = DvplData.low_compression
      else:
        sign.compress_level = DvplData.no_compression
      return sign

    def as_bytes(self):
      sign = self.origin_size.to_bytes(4, little_endian)
      sign += self.compress_size.to_bytes(4, little_endian)
      sign += self.compress_hash_sum.to_bytes(4, little_endian)
      sign += self.compress_level.to_bytes(4, little_endian)
      sign += b'DVPL'
      return sign

  def __init__(self):
    self.data = b''

  def load_from_dvpl(self, data):
    if not type(data) is bytes:
      self._log.error(f'data type ({type(data)}), expect (bytes)')
      return False

    sign = DvplData.Sign()
    status, lz4_archive = sign.load_from_dvpl(data)
    if not status:
      self._log.error(f"Sign didn't load")
      return False
    elif sign.compress_size != len(lz4_archive):
      self._log.error(f"File corruption: {sign.compress_size} != {len(lz4_archive)}")
      return False

    if sign.origin_size == sign.compress_size:  # compress isn't use
      self._log.debug(f'Data compress level: {DvplData.no_compression}')
      self.data = lz4_archive
    else:
      self._log.debug(f'Data compress level: {sign.compress_level}')
      decompress = b'\0' * sign.origin_size
      unpacked_data = lz4b.decompress(lz4_archive, uncompressed_size=len(decompress))
      if len(unpacked_data) != sign.origin_size:
        return False

      self.data = unpacked_data
    return True

  def as_dvpl(self):
    max_plane_len = 64

    if len(self.data) > max_plane_len:
      compressed = lz4b.compress(self.data,
                                 mode='high_compression',
                                 acceleration=1,
                                 compression=2)
    else:
      compressed = self.data

    sign = DvplData.Sign.create_from_data(self.data, compressed)
    return compressed + sign.as_bytes()

  def load_from_file(self, filename):
    if not os.path.exists(filename):
      self._log.error(f'File {filename} is not exists')
      return False

    with open(filename, 'rb') as dvpl:
      data = dvpl.read()

    return self.load_from_dvpl(data)
