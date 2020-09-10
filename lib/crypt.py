pat = b'abcdefghijklmnopqrstuvwxyz0123456789'

def td_asctonum(code):
  if code in b'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
    code += 0x20
    
  if code not in pat:
    return None
  
  return pat.index(code)

def td_numtoasc(code):
  if code < 36:
    return pat[code]
    
  return None

gword = [
  b'SjiW8JO7mH65awR3B4kTZeU90N1szIMrF2PC',
  b'04A1EF7rCH3fYl9UngKRcObJD6ve8W5jdTta',
  b'brU5XqY02ZcA3ygE6lf74BIG9LF8PzOHmTaC',
  b'2I1vF5NMYd0L68aQrp7gTwc4RP9kniJyfuCH',
  b'136HjBIPWzXCY9VMQa7JRiT4kKv2FGS5s8Lt',
  b'Hwrhs0Y1Ic3Eq25a6t8Z7TQXVMgdePuxCNzJ',
  b'WAmkt3RCZM829P4g1hanBluw6eVGSf7E05oX',
  b'dMxreKZ35tRQg8E02UNTaoI76wGSvVh9Wmc1',
  b'i20mzKraY74A6qR9QM8H3ecUkBlpJC1nyFSZ',
  b'XCAUP6H37toQWSgsNanf0j21VKu9T4EqyGd5',
  b'dFZPb9B6z1TavMUmXQHk7x402oEhKJD58pyG',
  b'rg8V3snTAX6xjuoCYf519BzWRtcMl2OiZNeI',
  b'dZe620lr8JW4iFhNj3K1x59Una7PXsLGvSmB',
  b'5yaQlGSArNzek6MXZ1BPOE3xV470h9KvgYmb',
  b'f12CVxeQ56YWd7OTXDtlnPqugjJikELayvMs',
  b'9Qoa5XkM6iIrR7u8tNZgSpbdDUWvwH21Kyzh',
  b'AqGWke65Y2ufVgljEhMHJL01D8Zptvcw7CxX',
  b't960P2inR8qEVmAUsDZIpH5wzSXJ43ob1kGW',
  b'4l6SAi2KhveRHVN5JGcmx9jOC3afB7wF0ITq',
  b'tEOp6Xo87QzPbn24J3i9FjWKS1lIBVaMZeHU',
  b'zx27DH915lhs04aMJOgf6Z3pyERrGndiLwIe',
  b'8XxOBzZ02hUWDQfvL471q9RC6sAaJVFuTMdG',
  b'jON0i4C6Z3K97DkbqSypH8lRmx5o2eIwXas1',
  b'OIGT0ubwH1x6hCvEgBn274A5Q8K9e3YyzWlm',
  b'zgejY41CLwRNabovBUP2Aql7FVM8uEDXZQ0c',
  b'Z2MpQE91gdRLYJ8bGIWyOfc4v03Hjzs6VlU5',
  b't6PuvrBXeoHk5FJW08DYQSI49GCwZ27cA1UK',
  b'FiBA53IMW97kYNz82GhHf1yUCdL0nlvRD46s',
  b'2Vz3b06h54jmc7a8AIYtNHM1iQU9wBXWyJkR',
  b'wyI42azocV3UOX6fk579hMH8eEGJsgFuBmqb',
  b'TxmnK4ljJ9iroY8vVtg3Rae2L516fBWUuXAS',
  b'z6Y1bPrJEln0uWeLKkjo9IZ2y7ROcFHqBm54',
  b'x064LFB39TsXeryqvt2pZN8QIERuWAVUmwjJ',
  b'76qg85yB31uH90YbZofsjKrRGiTVndAEtFMx',
  b'WjwTEbCA752kq89shcaLB1xO64rgMYnoFiJQ',
  b'u6307O4J2DeZs8UYyjlzfX91KGmavEdwTRSg'
]

def td_decrypt(data, key):
  kdx = 0
  ret = []

  for idx, code in enumerate(data):    
    while True:
      if kdx >= len(key):
        kdx = 0
      
      kcode = key[kdx]
      knum = td_asctonum(kcode)
      
      if knum is None:
        kdx += 1
        continue
      
      break

    if code not in gword[knum]:
      return None
    
    cpos = gword[knum].index(code)
    ret.append(td_numtoasc(cpos))
    
    kdx += 1

  return bytes(ret)
