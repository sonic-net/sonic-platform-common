"""JSON corpus for platform-base's json.loads: input<TAB>Python's answer."""
import json, random, sys
random.seed(7)
seeds = [
    '{"@odata.id": "/redfish/v1/SessionService/Sessions/abc", "Id": "abc", "UserName": "u", "Oem": {}}',
    '{"Members": [{"@odata.id": "/redfish/v1/SessionService/Sessions/x1"}, {"@odata.id": "/x/y2"}], "Members@odata.count": 2}',
    '{"error": {"code": "Base.1.8.ResourceNotFound", "message": "The requested resource of type X was not found.", "@Message.ExtendedInfo": []}}',
    '{"PercentComplete": 100, "TaskStatus": "OK", "Messages": [{"MessageId": "ResourceEvent.1.0.UpdateSuccessful", "MessageArgs": ["MGX_FW_BMC_0", "x"]}]}',
    '{"Id": "BMC_eeprom", "Model": "P4501", "SerialNumber": "MT2234X00123", "Status": {"State": "Enabled", "Health": "OK"}, "Version": 1.5e2, "Neg": -0.0, "Big": 123456789012345678901234567890}',
    '[1, 2.5, -3e-2, true, false, null, "a\\u00e9\\n\\t\\"\\\\\\/", [], {}, NaN, Infinity, -Infinity]',
    '{"@Message.ExtendedInfo": [{"MessageId": "Base.1.8.Success", "Message": "ok"}], "Password@Message.ExtendedInfo": [{"MessageId": "x.Error", "Message": "m", "Resolution": "r"}]}',
    '  {\n  "a" : [ 1 , 2 ] ,\r\n\t"b":{"c":"\\ud83d\\ude00"}}  ',
    '"just a string"', '42', '-0', '0.5', '1E400', '"\\u0041\\u00"',
]
alphabet = '{}[]",:\\ \n\t0123456789eE.-+ntfuNIaxzé\x01'
cases = set(seeds)
for s in seeds:
    for _ in range(300):
        t = list(s)
        for _ in range(random.randint(1, 3)):
            op = random.random()
            if op < 0.3 and t:
                del t[random.randrange(len(t))]
            elif op < 0.6:
                t.insert(random.randrange(len(t) + 1), random.choice(alphabet))
            elif op < 0.8 and t:
                t[random.randrange(len(t))] = random.choice(alphabet)
            else:
                t = t[:random.randrange(len(t) + 1)]
        cases.add(''.join(t))
out = []
for s in sorted(cases):
    try:
        v = json.loads(s)
        ans = repr(v)
        json.dumps(v, ensure_ascii=False).encode('utf-8')
    except UnicodeEncodeError:
        continue  # a lone surrogate: not representable natively
    except json.JSONDecodeError as e:
        ans = 'JSONDecodeError ' + str(e)
    except Exception as e:
        ans = type(e).__name__ + ' ' + str(e)
    out.append(json.dumps(s) + '\t' + ans)
sys.stdout.write('\n'.join(out) + '\n')
print(len(out), file=sys.stderr)
