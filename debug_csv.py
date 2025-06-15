import csv

# Extract unique products from CSV
products = set()
statuses = set()

try:
    with open('Projects.csv', 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            # Find HS _Product column
            for key, value in row.items():
                if 'hs _product' in key.lower():
                    if value and value.strip():
                        products.add(value.strip())
                
                if 'status' in key.lower():
                    if value and value.strip():
                        statuses.add(value.strip())

    print("=== UNIQUE PRODUCTS FROM HS _Product ===")
    for product in sorted(products):
        print(f"'{product}'")
    
    print(f"\nTotal products: {len(products)}")
    
    print("\n=== UNIQUE STATUSES ===")
    for status in sorted(statuses):
        print(f"'{status}'")
    
    print(f"\nTotal statuses: {len(statuses)}")

except FileNotFoundError:
    print("Projects.csv not found")
except Exception as e:
    print(f"Error: {e}")
