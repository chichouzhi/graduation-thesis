import sys

score = 90  # 可以后面接入真实评分逻辑

if score < 80:
    print("FAIL: Score too low:", score)
    sys.exit(1)
else:
    print("OK: Score", score)