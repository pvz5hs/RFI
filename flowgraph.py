import sys

def main():
    print("Script Name:", sys.argv[0])
    print("Arguments:")
    for i, arg in enumerate(sys.argv[1:], start=1):
        print(f"Argument {i}: {arg}")

if __name__ == "__main__":
    main()