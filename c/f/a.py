def main():
    try:
        num1 = int(input("Enter first integer: "))
        num2 = int(input("Enter second integer: "))
        avg = (num1 + num2) / 2
        print(f"The average is: {avg}")
    except ValueError:
        print("Invalid input. Please enter integers.")

if __name__ == "__main__":
    main()