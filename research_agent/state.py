from typing import TypedDict, List, Dict, Optional

# Định nghĩa tên 8 hạng mục để dễ quản lý và nhất quán
CATEGORY_BIOGRAPHY = "Biographical_Historical_Context"
CATEGORY_WORKS = "Major_Works_Core_Content"
CATEGORY_DOCTRINES = "Core_Philosophical_Doctrines_Ideas"
CATEGORY_TOPICS = "Views_on_Specific_Philosophical_Topics"
CATEGORY_RELATIONS = "Philosophical_Relationships_Interactions"
CATEGORY_CRITIQUES = "Critiques_Evaluations_of_Doctrines"
CATEGORY_METHODOLOGY = "Characteristic_Philosophical_Methodology"
CATEGORY_STYLE = "Argumentative_Style_Rhetoric"

ALL_RESEARCH_CATEGORIES = [
    CATEGORY_BIOGRAPHY,
    CATEGORY_WORKS,
    CATEGORY_DOCTRINES,
    CATEGORY_TOPICS,
    CATEGORY_RELATIONS,
    CATEGORY_CRITIQUES,
    CATEGORY_METHODOLOGY,
    CATEGORY_STYLE,
]

class PhilosopherResearchState(TypedDict):    
    philosopher_name: str
    
    # Quản lý vòng lặp qua các hạng mục
    all_categories: List[str]           # Danh sách 8 hạng mục
    current_category_index: int         # Chỉ số của hạng mục hiện tại (0-7)
    current_category_name: Optional[str] # Tên của hạng mục đang được xử lý
    
    # Dữ liệu tạm thời cho hạng mục hiện tại đang được xử lý trong vòng lặp
    category_specific_queries: List[str]
    category_specific_search_results: List[Dict]
    # category_specific_extracted_data: List[Dict] # Đổi tên để rõ ràng hơn
    current_category_extracted_info: List[Dict] # Thông tin trích xuất cho hạng mục hiện tại

    # Nơi lưu trữ tất cả thông tin đã trích xuất, được phân loại theo từng hạng mục
    # Key sẽ là tên hạng mục (vd: CATEGORY_BIOGRAPHY)
    accumulated_extracted_information: Dict[str, List[Dict]] 
    
    # Kết quả cuối cùng
    final_synthesized_profile: Optional[Dict] 
    
    # Thống kê tổng hợp
    total_generated_queries_count: int
    total_search_results_count: int

    # Quản lý lỗi và vòng lặp tinh chỉnh (nếu có)
    error_messages: List[str]
    refinement_iterations: int # Hiện tại chưa dùng cho vòng lặp tinh chỉnh, nhưng giữ lại 