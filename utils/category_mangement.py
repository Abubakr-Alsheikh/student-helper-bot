import os
import pandas as pd

from config import EXCEL_FILE_BASHAR
from utils import database


def populate_categories_data():
    """Populates the database with main and subcategories from your Excel file."""
    excel_file_path = EXCEL_FILE_BASHAR  # Replace with your Excel file
    df = pd.read_excel(excel_file_path) 

    for _, row in df.iterrows():
        main_category = row["التصنيف الرئيسي مدقق"]

        # Insert main category if it doesn't exist
        database.execute_query("INSERT OR IGNORE INTO main_categories (name) VALUES (?)", (main_category,))
        main_category_id = database.get_data("SELECT id FROM main_categories WHERE name = ?", (main_category,))[0][0] 

        subcategories = row["التصنيفات الفرعية مدققة"].split('،')  

        for subcategory in subcategories:
            subcategory = subcategory.strip()
            # Insert subcategory if it doesn't exist
            database.execute_query("INSERT OR IGNORE INTO subcategories (name) VALUES (?)", (subcategory,))
            subcategory_id = database.get_data("SELECT id FROM subcategories WHERE name = ?", (subcategory,))[0][0]

            # Create the link
            database.execute_query(
                "INSERT OR IGNORE INTO main_sub_links (main_category_id, subcategory_id) VALUES (?, ?)", 
                (main_category_id, subcategory_id)
            )


def get_subcategory_name(subcategory_id):
    """Fetches the name of a subcategory by its ID."""
    subcategory_name = database.get_data("SELECT name FROM subcategories WHERE id = ?", (subcategory_id,))
    return subcategory_name[0][0]

def get_main_categories(page=1, per_page=10):
    """Fetches a paginated list of main categories with IDs."""
    categories = database.get_data("SELECT id, name FROM main_categories LIMIT ? OFFSET ?", (per_page, (page - 1) * per_page))
    return categories

def get_subcategories(main_category_id, page=1, per_page=10):
    """Fetches a paginated list of subcategories with IDs."""
    subcategories = database.get_data(
        '''
        SELECT s.id, s.name 
        FROM subcategories s
        JOIN main_sub_links msl ON s.id = msl.subcategory_id
        WHERE msl.main_category_id = ?
        LIMIT ? OFFSET ?
        ''', 
        (main_category_id, per_page, (page - 1) * per_page)
    )
    return subcategories

def get_subcategories_all(page=1, per_page=10):
    """Fetches a paginated list of all subcategories with IDs."""
    subcategories = database.get_data("SELECT id, name FROM subcategories LIMIT ? OFFSET ?", (per_page, (page - 1) * per_page))
    return subcategories

def get_material_path(main_category_name, subcategory_name, material_number, format):
    """Constructs the file path for the requested material.
    
    Important: This function assumes your folder structure and file naming conventions.
    """
    base_path = "template_maker\Main_Classification_Structure"  # Update if needed
    folder_name = f"نموذج {material_number}"
    file_name = folder_name

    if format == 'pdf':
        file_name += '.pdf'
    elif format == 'video':
        file_name += '.mp4'
    # Add other formats as needed

    return os.path.join(base_path, main_category_name, subcategory_name, folder_name, file_name) 


def get_main_categories_by_subcategory(subcategory_id, page=1, per_page=10):
    """Fetches a paginated list of main categories linked to a specific subcategory."""
    main_categories = database.get_data(
        '''
        SELECT mc.id, mc.name 
        FROM main_categories mc
        JOIN main_sub_links msl ON mc.id = msl.main_category_id
        WHERE msl.subcategory_id = ?
        LIMIT ? OFFSET ?
        ''', 
        (subcategory_id, per_page, (page - 1) * per_page)
    )
    return main_categories