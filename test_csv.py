import pandas as pd

def test_csv_read():
    """Test reading a CSV file"""
    try:
        # Read the CSV file
        df = pd.read_csv('test_data.csv')
        
        # Print basic info
        print(f"DataFrame shape: {df.shape}")
        print(f"DataFrame columns: {df.columns.tolist()}")
        
        # Print all rows
        print("\nAll rows in the dataframe:")
        for idx, row in df.iterrows():
            print(f"Row {idx}: {row['text'][:30]}... [Aspect: {row['aspect']}]")
        
        # Count rows
        print(f"\nTotal rows: {len(df)}")
        
    except Exception as e:
        print(f"Error reading CSV: {str(e)}")

if __name__ == "__main__":
    test_csv_read() 