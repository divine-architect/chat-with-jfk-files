import os
import logging
import time
import gc
from pdf2image import convert_from_path
from pytesseract import image_to_string
from multiprocessing import Pool, cpu_count
from tqdm import tqdm


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("ocr_process.log"),
        logging.StreamHandler()
    ]
)


INPUT_FOLDER = "jfk_files" 
OUTPUT_FOLDER = "txt_output/"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def get_processed_files():
    return {f.replace(".txt", "") for f in os.listdir(OUTPUT_FOLDER) if f.endswith(".txt")}


def extract_text_from_image(img):
    # Skip preprocessing entirely for speed
    # Use fast mode with legacy engine
    config = '--psm 6 --oem 1 -c tessdata_fast_mode=1'
    text = image_to_string(img, lang='eng', config=config)
    
    return text


def process_pdf(pdf_path):
    pdf_name = os.path.basename(pdf_path).replace(".pdf", "")
    txt_path = os.path.join(OUTPUT_FOLDER, f"{pdf_name}.txt")
    
    try:
        logging.info(f"Starting to process {pdf_name}")
        
      
        with open(txt_path, "w", encoding="utf-8") as f:
            # Convert PDF pages to images at lower DPI
            logging.info(f"{pdf_name}: Converting PDF to images")
            images = convert_from_path(pdf_path, dpi=150)
            
            
            for i, img in enumerate(images):
                current_page = i + 1
                logging.info(f"{pdf_name}: OCR on page {current_page}")
                text = extract_text_from_image(img)
                f.write(f"--- PAGE {current_page} ---\n{text}\n\n")
                
             
                del img
                gc.collect()
            
         
            del images
            gc.collect()
        
        logging.info(f"Completed processing {pdf_name}")
        return f"{pdf_name} - DONE"
    
    except Exception as e:
        logging.error(f"Error processing {pdf_name}: {str(e)}", exc_info=True)
        return f"{pdf_name} - FAILED ({str(e)})"


def get_optimal_workers():
    available_cpus = cpu_count()

    return max(1, min(available_cpus // 2, 4))

# Main execution
if __name__ == "__main__":
    from multiprocessing import freeze_support
    freeze_support()  
    
    start_time = time.time()
    
  
    pdf_files = [os.path.join(INPUT_FOLDER, f) for f in os.listdir(INPUT_FOLDER) if f.endswith(".pdf")]
    total_pdfs = len(pdf_files)
    
  
    processed = get_processed_files()
    pdf_files = [f for f in pdf_files if os.path.basename(f).replace(".pdf", "") not in processed]
    
    workers = get_optimal_workers()
    logging.info(f"Starting OCR processing of {len(pdf_files)} PDFs ({total_pdfs - len(pdf_files)} already processed)")
    logging.info(f"Using {workers} worker processes with Tesseract OCR (optimized for speed)")
    
 
    with Pool(processes=workers) as pool:
        results = list(tqdm(pool.imap(process_pdf, pdf_files), total=len(pdf_files)))
    

    elapsed_time = time.time() - start_time
    hours, remainder = divmod(elapsed_time, 3600)
    minutes, seconds = divmod(remainder, 60)
    

    success_count = sum(1 for res in results if "DONE" in res)
    fail_count = sum(1 for res in results if "FAILED" in res)
    
    logging.info(f"OCR Processing Completed!")
    logging.info(f"Successful: {success_count}, Failed: {fail_count}")
    logging.info(f"Total processing time: {int(hours)}h {int(minutes)}m {int(seconds)}s")
    # AI logger
    print(f"\nOCR Processing Summary:")
    print(f"Processed: {len(pdf_files)}, Successful: {success_count}, Failed: {fail_count}")
    print(f"Total processing time: {int(hours)}h {int(minutes)}m {int(seconds)}s")
    

    if fail_count > 0:
        logging.info("Failed documents:")
        for res in results:
            if "FAILED" in res:
                logging.info(res)
                print(res)

#works
def extract_text_from_pdf(path: str) -> str:

    images = convert_from_path(path, dpi=150)
    config = '--psm 6 --oem 1 -c tessdata_fast_mode=1'
    text = "".join(image_to_string(img, lang='eng', config=config) for img in images)
    return text