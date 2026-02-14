
import json
import re

def main():
    with open('output.txt', 'r') as f:
        content = f.read()
        # Extract JSON part
        match = re.search(r"DEBUG RAW USERS: ({.*})", content)
        if match:
            data = eval(match.group(1)) # It printed python dict string representation, not valid JSON (None vs null)
            # Safe eval for python repr
            
            users = data.get('users', [])
            target_id = 85751735
            
            found = [u for u in users if u.get('telegramId') == target_id]
            print(f"Users with telegramId {target_id}:")
            for u in found:
                print(f"- Username: {u.get('username')}")
                print(f"  UUID: {u.get('uuid')}")
                print(f"  Status: {u.get('status')}")
                print(f"  ShortUUID: {u.get('shortUuid')}")
                print("---")
        else:
            print("Could not find JSON in output.")

if __name__ == "__main__":
    main()
