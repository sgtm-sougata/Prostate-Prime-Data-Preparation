
# Prostate Prime data prepareation
# Step 1: De-identification
# Step 2: Read RTSTRUCT Structure Name
# Step 3: Harmonization based on Structure
# Step 4: Remove duplicate and blank Structure 
# Step 5: Save in a directory


# python module
import os
import re
import shutil
import pydicom
import numpy as np
import pandas as pd
from tqdm import tqdm
from fnmatch import fnmatch

df = pd.read_csv("Prostate prime d73 all structure name - Sheet4.csv")

original_names_array = df['original_label'].to_numpy()
new_names_array = df['modified_label'].to_numpy()
csvFile_array = np.column_stack((original_names_array, new_names_array))


def rtstruct_harmonization(ds, csvFile_array, filename):
    """
    Harmonizes the ROI names in a DICOM RTSTRUCT object based on a CSV file.
    
    Parameters:
    - ds: pydicom Dataset object
    - csvFile_array: numpy array containing original and new ROI names
    - filename: path to save the modified RTSTRUCT DICOM file
    """
    try:
        # Extract the original ROI names from the CSV file array
        orig_name = csvFile_array[:, 0]

        # Loop through each ROI in the StructureSetROISequence
        for i in range(len(ds.StructureSetROISequence)):
            ROI_name = ds.StructureSetROISequence[i].ROIName
            PatientID = ds.PatientID  # This is not used in the current code
            
            if ROI_name in orig_name:
                # Find the index of the original ROI name in the CSV array
                loc = np.where(orig_name == ROI_name)
                
                # Update the ROI name with the new value from the CSV file
                ds.StructureSetROISequence[i].ROIName = csvFile_array[loc, 1][0][0]
        
        # Save the modified RTSTRUCT DICOM file
        ds.save_as(filename)
    
    except Exception as e:
        print(f"An error occurred: {e}")



from pydicom.dataset import Dataset
def remove_duplicate_and_blank_rois_and_contours(rtstruct_path, output_path):
    # Load the existing RTSTRUCT file
    ds = pydicom.dcmread(rtstruct_path)

    if 'StructureSetROISequence' not in ds:
        raise ValueError("No StructureSetROISequence found in the DICOM file.")

    if 'ROIContourSequence' not in ds:
        raise ValueError("No ROIContourSequence found in the DICOM file.")
    
    # Create dictionaries to track unique ROIs and contours
    roi_dict = {}
    unique_rois = []
    unique_contours = []
    
    # Process ROIs
    for roi in ds.StructureSetROISequence:
        roi_name = roi.ROIName
        roi_number = roi.ROINumber
        
        if roi_name not in roi_dict:
            roi_dict[roi_name] = roi_number
            unique_rois.append(roi)

    # Track used ROI numbers
    roi_numbers = {roi.ROINumber for roi in unique_rois}

    # Process contours
    contour_dict = {}
    for contour in ds.ROIContourSequence:
        referenced_roi_number = contour.ReferencedROINumber

        # Check if the referenced ROI number is valid
        if referenced_roi_number in roi_numbers:
            # Check if the contour data is not empty
            if hasattr(contour, 'ContourSequence') and len(contour.ContourSequence) > 0:
                roi_name = None
                for roi in unique_rois:
                    if roi.ROINumber == referenced_roi_number:
                        roi_name = roi.ROIName
                        break
                
                if roi_name:
                    if (roi_name, referenced_roi_number) not in contour_dict:
                        contour_dict[(roi_name, referenced_roi_number)] = contour
                        unique_contours.append(contour)

    # Update the dataset with unique ROIs and contours
    ds.StructureSetROISequence = unique_rois
    ds.ROIContourSequence = unique_contours
    
    # Save the modified RTSTRUCT file
    ds.save_as(output_path)


def clean_data(root_dir, output_dir):
    for root, dir, filename in os.walk(root_dir):
        for filenames in tqdm(filename, desc = f"{os.path.basename(root)}"):
                if filenames.endswith(".dcm"):
                    fpath = os.path.join(root, filenames)
                    try:
                        ds = pydicom.dcmread(fpath)
                        patient_id = ds.PatientID
                        patient_dir = os.path.join(output_dir, patient_id)
                        os.makedirs(patient_dir, exist_ok=True)

                        if ds.Modality == "RTSTRUCT":
                            cdir = os.path.join(patient_dir, f"{filenames}")
                            rtstruct_harmonization(ds, csvFile_array, fpath)
                            remove_duplicate_and_blank_rois_and_contours(fpath, cdir)
                        else:
                            cdir = os.path.join(patient_dir, f"{filenames}")
                            shutil.copy(fpath, cdir)
                    except:
                        print(f"dicom reading error - {fpath}")

root_dir = "prostate_harmonize"
output_dir = "data"
clean_data(root_dir=root_dir, output_dir=output_dir)