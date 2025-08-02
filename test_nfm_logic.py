#!/usr/bin/env python3
"""
Test script to verify NFM filtering logic for export_history function
"""

from datetime import datetime, timedelta

def test_nfm_filtering_logic():
    """Test the logic for filtering out machines that were NFM on previous day"""
    
    # Simulate the logic from export_history function
    def get_nfm_machines_for_date(date_obj):
        # This simulates the SQL queries in the export_history function
        
        # Example data - in real scenario this would come from database
        nfm_records = [
            {'machine_id': 1, 'reported_date': datetime(2024, 1, 15), 'fixed_date': None},  # Machine 1: NFM on Jan 15, not fixed
            {'machine_id': 2, 'reported_date': datetime(2024, 1, 15), 'fixed_date': datetime(2024, 1, 16)},  # Machine 2: NFM on Jan 15, fixed on Jan 16
            {'machine_id': 3, 'reported_date': datetime(2024, 1, 16), 'fixed_date': None},  # Machine 3: NFM on Jan 16, not fixed
        ]
        
        # Get NFM machines for the specific date
        current_nfm_ids = set()
        for record in nfm_records:
            if (record['reported_date'].date() == date_obj and 
                (record['fixed_date'] is None or record['fixed_date'].date() > date_obj)):
                current_nfm_ids.add(record['machine_id'])
        
        # Get machines that were NFM on the previous day and weren't repaired
        previous_date = date_obj - timedelta(days=1)
        previous_nfm_ids = set()
        for record in nfm_records:
            if (record['reported_date'].date() == previous_date and 
                (record['fixed_date'] is None or record['fixed_date'].date() > date_obj)):
                previous_nfm_ids.add(record['machine_id'])
        
        # Combine both sets
        all_non_functioning_ids = current_nfm_ids.union(previous_nfm_ids)
        
        return current_nfm_ids, previous_nfm_ids, all_non_functioning_ids
    
    # Test scenarios
    test_date = datetime(2024, 1, 16).date()  # January 16, 2024
    
    current_nfm, previous_nfm, all_nfm = get_nfm_machines_for_date(test_date)
    
    print(f"Testing NFM filtering for date: {test_date}")
    print(f"Machines NFM on current date ({test_date}): {current_nfm}")
    print(f"Machines NFM on previous date ({test_date - timedelta(days=1)}): {previous_nfm}")
    print(f"All machines to filter out: {all_nfm}")
    
    # Expected results:
    # - Machine 1: Should be in previous_nfm (NFM on Jan 15, not fixed by Jan 16)
    # - Machine 2: Should not be in any set (NFM on Jan 15, but fixed on Jan 16)
    # - Machine 3: Should be in current_nfm (NFM on Jan 16, not fixed)
    
    expected_current = {3}
    expected_previous = {1}
    expected_all = {1, 3}
    
    print(f"\nExpected current NFM: {expected_current}")
    print(f"Expected previous NFM: {expected_previous}")
    print(f"Expected all NFM: {expected_all}")
    
    print(f"\nTest results:")
    print(f"Current NFM correct: {current_nfm == expected_current}")
    print(f"Previous NFM correct: {previous_nfm == expected_previous}")
    print(f"All NFM correct: {all_nfm == expected_all}")
    
    if current_nfm == expected_current and previous_nfm == expected_previous and all_nfm == expected_all:
        print("✅ All tests passed! The logic works correctly.")
    else:
        print("❌ Some tests failed. Please check the logic.")

if __name__ == "__main__":
    test_nfm_filtering_logic() 