import csv

# Extract unique products from CSV
products = set()
statuses = set()
cities = set()

try:
    with open('Projects.csv', 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            # Find product column
            for key, value in row.items():
                if 'hs _product' in key.lower() or 'product' in key.lower():
                    if value and value.strip():
                        products.add(value.strip())
                
                if 'status' in key.lower():
                    if value and value.strip():
                        statuses.add(value.strip())
                        
                if 'city' in key.lower():
                    if value and value.strip():
                        cities.add(value.strip())

    print("=== UNIQUE PRODUCTS ===")
    for product in sorted(products):
        print(f"'{product}'")
    
    print(f"\nTotal products: {len(products)}")
    
    print("\n=== UNIQUE STATUSES ===")
    for status in sorted(statuses):
        print(f"'{status}'")
    
    print(f"\nTotal statuses: {len(statuses)}")
    
    print("\n=== UNIQUE CITIES ===")
    for city in sorted(cities):
        print(f"'{city}'")
    
    print(f"\nTotal cities: {len(cities)}")

except FileNotFoundError:
    print("Projects.csv not found")
except Exception as e:
    print(f"Error: {e}") 