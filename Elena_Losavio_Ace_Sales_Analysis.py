import pandas as pd
import os

# ----------- 1. Load Dataset -----------
def load_main_dataset(path):
    df = pd.read_csv(path, encoding='latin1').drop_duplicates()
    return df

# ----------- 2. Inference for Missing Region & Country -----------
def fill_region_country(df):
    country_map = df[(df['Region'].notnull()) & (df['Country'] != 'England')][['Country', 'Region']] \
        .drop_duplicates().set_index('Country')['Region'].to_dict()
    city_map = df[df['Region'].notnull()][['City', 'Region']] \
        .drop_duplicates().set_index('City')['Region'].to_dict()
    region_country_map = df[df['Country'].notnull()][['Region', 'Country']] \
        .drop_duplicates().set_index('Region')['Country'].to_dict()

    df['Region'] = df['Region'].fillna(df['Country'].map(country_map))
    df['Region'] = df['Region'].fillna(df['City'].map(city_map))
    df['Country'] = df['Country'].fillna(df['Region'].map(region_country_map))
    return df

# ----------- 3. Impute Missing Discounts & List Price -----------
def impute_discounts(df):
    known_mask = df['Discount'].notnull() & (df['Discount'] != 0)
    df.loc[known_mask, 'List Price'] = df.loc[known_mask, 'Sales'] / (
        df.loc[known_mask, 'Quantity'] * (1 - df.loc[known_mask, 'Discount'])
    )

    avg_price = df.groupby('Product ID')['List Price'].mean().to_dict()
    df['List Price'] = df['List Price'].fillna(df['Product ID'].map(avg_price))

    missing_mask = df['Discount'].isnull()
    df.loc[missing_mask, 'Discount'] = 0  # 👈 Directly fill NULL discounts with 0

    return df

# ----------- 4. Fill Category & Segment -----------
def fill_category_segment(df):
    inferred = df[df['Category'].notnull()][['Sub-Category', 'Category']] \
        .drop_duplicates().set_index('Sub-Category')['Category'].to_dict()
    manual_map = {
        'Seasoning Mixes': 'Food - Spices',
        'Dog Supplies': 'Pet Supplies',
        'Audio Recording Devices': 'Electronics',
        'Seeds & Nuts': 'Food - Snacks',
        'Healthy Meals': 'Food - Salads',
    }

    df['Category'] = df['Category'].fillna(df['Sub-Category'].map(inferred))
    df['Category'] = df['Category'].fillna(df['Sub-Category'].map(manual_map))

    split = df['Category'].str.split(' - ', n=1, expand=True)
    df['Category'] = split[0]
    df['Segment'] = split[1].fillna(split[0])
    return df

# ----------- 5. Correct Region/Country Based on External Reference -----------
def correct_region_country(df, reference_path):
    ref = pd.read_csv(reference_path)
    city_dict = ref[['City', 'Region', 'Country']] \
        .drop_duplicates(subset='City').set_index('City')[['Region', 'Country']] \
        .apply(tuple, axis=1).to_dict()

    def correct(row):
        expected = city_dict.get(row['City'])
        if expected and (row['Region'], row['Country']) != expected:
            row['Region'], row['Country'] = expected
            row['Correction_Flag'] = 'Corrected'
        elif expected:
            row['Correction_Flag'] = 'OK'
        else:
            row['Correction_Flag'] = 'City not in reference'
        return row

    return df.apply(correct, axis=1)

# ----------- 6. Standardize Region Names -----------
def standardize_region(df):
    df['Region'] = df['Region'].replace({
        'Yorkshire and the Humber': 'Yorkshire & the Humber'
    })
    return df

# ----------- 7. Fix Negative Discounts by Replacing with 0 -----------
def fix_negative_discounts(df):
    neg_discount_rows = df[df['Discount'] < 0]
    neg_sales_total = neg_discount_rows['Sales'].sum()
    overall_sales_total = df['Sales'].sum()
    share = neg_sales_total / overall_sales_total

    df.loc[df['Discount'] < 0, 'Discount'] = 0
    return df

# ----------- 8. Save Cleaned Dataset -----------
def save_clean_data(df, output_path):
    df.to_csv(output_path, index=False)
    print(f"\n✅ Cleaned data saved to: {output_path}")

# ----------- 9. Main Execution Block -----------
if __name__ == "__main__":
    input_path = "Ace_Superstore_Retail_Dataset.csv"
    reference_path = "Store_Locations.csv"
    output_path = os.path.join(os.getcwd(), "Elena_Losavio_final_cleaned_sales.csv")

    df = load_main_dataset(input_path)
    df = fill_region_country(df)
    df = impute_discounts(df)
    df = fill_category_segment(df)
    df = correct_region_country(df, reference_path)
    df = standardize_region(df)
    df = fix_negative_discounts(df)  # 👈 Final fix for bad discounts

    save_clean_data(df, output_path)
