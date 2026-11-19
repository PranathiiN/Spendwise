"""Starter training examples for the default categories.

These give new users sensible suggestions before they've recorded much. As soon
as a user records their own transactions, their choices outweigh these.
Keys must match the system category names in app/db/seed.py.
"""

SEED_EXAMPLES: dict[str, list[str]] = {
    # Expense
    "Food & Dining": [
        "swiggy order", "zomato order", "lunch", "dinner", "breakfast", "restaurant", "cafe coffee",
        "starbucks", "chai", "tea", "snacks", "groceries", "grocery store", "bigbasket", "blinkit",
        "zepto", "instamart", "dmart", "vegetables", "fruits", "milk", "bakery", "pizza", "dominos",
        "mcdonalds", "kfc", "burger king", "biryani", "food court", "canteen", "tiffin", "sweets",
    ],
    "Housing": [
        "rent", "house rent", "flat rent", "maintenance charges", "society maintenance", "home loan emi",
        "property tax", "plumber", "electrician", "house repair", "pg rent", "hostel fee", "deposit",
    ],
    "Transportation": [
        "uber", "ola", "rapido", "auto rickshaw", "cab", "taxi", "metro card", "metro recharge",
        "bus ticket", "petrol", "diesel", "fuel", "parking", "toll", "fastag", "car service",
        "bike service", "local train", "car insurance", "bike insurance",
    ],
    "Shopping": [
        "amazon", "flipkart", "myntra", "ajio", "meesho", "nykaa", "clothes", "shoes", "shirt",
        "jeans", "dress", "electronics", "headphones", "phone case", "mobile phone", "laptop",
        "furniture", "ikea", "decathlon", "mall", "gift for", "watch", "bag",
    ],
    "Utilities": [
        "electricity bill", "power bill", "water bill", "gas cylinder", "lpg", "piped gas",
        "internet bill", "broadband", "wifi", "jio fiber", "airtel", "mobile recharge", "phone bill",
        "postpaid bill", "dth recharge", "tata play",
    ],
    "Entertainment": [
        "movie tickets", "pvr", "inox", "bookmyshow", "concert", "game", "gaming", "steam",
        "playstation", "bowling", "amusement park", "party", "drinks", "pub", "bar", "club",
    ],
    "Healthcare": [
        "doctor", "hospital", "clinic", "pharmacy", "medicines", "apollo pharmacy", "medplus",
        "pharmeasy", "1mg", "lab test", "blood test", "dentist", "eye checkup", "health insurance",
        "physiotherapy", "consultation fee",
    ],
    "Education": [
        "school fees", "college fees", "tuition", "coaching", "course", "udemy", "coursera",
        "books", "stationery", "exam fee", "certification", "workshop", "byjus", "unacademy",
    ],
    "Travel": [
        "flight", "flight tickets", "indigo", "air india", "train ticket", "irctc", "hotel",
        "oyo", "airbnb", "makemytrip", "goibibo", "holiday", "trip", "vacation", "visa fee",
        "luggage", "resort", "sightseeing",
    ],
    "Subscriptions": [
        "netflix", "amazon prime", "prime video", "hotstar", "disney plus", "spotify",
        "youtube premium", "apple music", "icloud", "google one", "chatgpt plus", "subscription",
        "membership", "gym membership", "zee5", "sonyliv",
    ],
    "Personal Care": [
        "haircut", "salon", "barber", "spa", "massage", "parlour", "cosmetics", "skincare",
        "grooming", "manicure", "gym", "yoga class",
    ],
    "Other Expense": [
        "misc", "miscellaneous", "donation", "charity", "fine", "penalty", "bank charges",
        "atm fee", "courier", "laundry", "dry cleaning", "pet food", "vet",
    ],
    # Income
    "Salary": ["salary", "monthly salary", "salary credited", "payroll", "pay slip", "wages", "stipend", "bonus"],
    "Freelance": ["freelance", "freelance project", "client payment", "consulting fee", "upwork", "fiverr", "contract work"],
    "Business": ["business income", "sales", "shop sales", "customer payment", "invoice paid", "revenue"],
    "Investment Income": [
        "dividend", "interest", "fd interest", "savings interest", "mutual fund redemption",
        "stock sale", "capital gains", "rental income", "zerodha", "groww",
    ],
    "Gift": ["gift", "birthday gift", "wedding gift", "gift money", "shagun", "received from parents"],
    "Refund": ["refund", "amazon refund", "flipkart refund", "cashback", "reversal", "return refund", "tax refund"],
    "Other Income": ["other income", "sold old phone", "sold", "reimbursement", "prize", "lottery", "friend paid back"],
}
