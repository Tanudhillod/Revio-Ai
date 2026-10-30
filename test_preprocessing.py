
from modules.preprocessing import load_reviews, load_operations

reviews = load_reviews("data/raw/sample_reviews.csv")
operations = load_operations("data/raw/sample_operations.csv")

print("Reviews loaded:", len(reviews))
print("Operations loaded:", len(operations))

print("\nReview preview:")
print(reviews.head())

print("\nOperations preview:")
print(operations.head())

print("\nMissing review values:")
print(reviews.isnull().sum())
