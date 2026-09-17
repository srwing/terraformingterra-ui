import collections
import json
import os

input_filename = "posts.json"
output_filename = "clean_labels.json"

# Verification step
if not os.path.exists(input_filename):
    print(f"Error: Could not find '{input_filename}' in this folder.")
    print("Please make sure the script is running in the same directory as your JSON file.")
    exit()

print(f"Success! Found '{input_filename}'. Mapping posts by their actual categories array...")

try:
    with open(input_filename, "r", encoding="utf-8") as f:
        posts = json.load(f)
        print(f"Loaded {len(posts)} posts from '{input_filename}'.")
    # Dictionary to group articles by their clean categories
    categories_map = collections.defaultdict(list)
    processed_count = 0

    for post in posts:
        title = post.get("title", "Untitled").strip()
        
        # Note: Your JSON uses a backend URL pattern, if it's missing we default to '#'
        url = post.get("url", "#").strip()
        
        # TARGET THE EXACT MATCH: The "categories" list array from your file
        post_categories = post.get("categories", [])

        if post_categories and isinstance(post_categories, list):
            processed_count += 1
            for category in post_categories:
                category_clean = category.strip()
                if category_clean:
                    # Append the lightweight search data needed for your menu layout
                    categories_map[category_clean].append({
                        "title": title,
                        "url": url
                    })

    # Output the optimized reverse lookup dictionary map
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(categories_map, f, indent=2, ensure_ascii=False)

    print(f"\nSuccess! Successfully processed {len(posts)} items.")
    print(f"Extracted {len(categories_map)} true structural categories.")
    print(f"Optimized category navigation written to: '{output_filename}'")

    # Print your final clean structural list
    print("\nYour True Blog Categories Found:")
    for cat in sorted(categories_map.keys()):
        print(f" - {cat} ({len(categories_map[cat])} articles)")

except json.JSONDecodeError:
    print(f"Error: '{input_filename}' has formatting issues. It is not valid JSON.")
except Exception as e:
    print(f"An unexpected error occurred: {e}")
