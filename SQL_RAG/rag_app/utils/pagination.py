"""Pagination utilities with backward compatibility"""

import math
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class PaginationHelper:
    """Helper class for pagination operations"""
    
    @staticmethod
    def calculate_pagination(
        total_items: int, 
        page_size: int = 15, 
        max_pages_to_show: int = 10
    ) -> Dict[str, Any]:
        """Calculate pagination parameters"""
        
        if total_items <= 0:
            return {
                'total_pages': 0,
                'page_size': page_size,
                'has_multiple_pages': False,
                'total_items': total_items,
                'start_item': 0,
                'end_item': 0
            }
        
        total_pages = math.ceil(total_items / page_size)
        
        return {
            'total_pages': total_pages,
            'page_size': page_size,
            'has_multiple_pages': total_pages > 1,
            'total_items': total_items,
            'current_page': 1,
            'start_item': 1,
            'end_item': min(page_size, total_items)
        }
    
    @staticmethod
    def get_page_info(
        page_num: int, 
        total_items: int, 
        page_size: int = 15
    ) -> Dict[str, int]:
        """Get information about current page range"""
        
        start_item = (page_num - 1) * page_size + 1
        end_item = min(page_num * page_size, total_items)
        
        return {
            'start_item': start_item,
            'end_item': end_item,
            'items_on_page': end_item - start_item + 1 if start_item <= end_item else 0
        }
    
    @staticmethod
    def get_valid_page_num(page_num: int, total_pages: int) -> int:
        """Get a valid page number within bounds"""
        
        if page_num < 1:
            return 1
        elif page_num > total_pages and total_pages > 0:
            return total_pages
        return page_num
    
    @staticmethod
    def get_page_display_pages(
        current_page: int, 
        total_pages: int, 
        max_pages_to_show: int = 10
    ) -> list:
        """Get list of page numbers to display in pagination UI"""
        
        if total_pages <= max_pages_to_show:
            return list(range(1, total_pages + 1))
        
        # Show pages around current page
        half_show = max_pages_to_show // 2
        start_page = max(1, current_page - half_show)
        end_page = min(total_pages, start_page + max_pages_to_show - 1)
        
        # Adjust if we're near the end
        if end_page - start_page < max_pages_to_show - 1:
            start_page = max(1, end_page - max_pages_to_show + 1)
        
        return list(range(start_page, end_page + 1))

# Backward compatibility functions
def calculate_pagination_legacy(
    total_queries: int, 
    page_size: int = 15
) -> Dict[str, Any]:
    """Legacy pagination calculation for backward compatibility"""
    
    helper = PaginationHelper()
    return helper.calculate_pagination(total_queries, page_size)

def get_page_slice_legacy(
    total_items: int, 
    page_num: int, 
    page_size: int = 15
) -> Dict[str, int]:
    """Legacy page info calculation for backward compatibility"""
    
    helper = PaginationHelper()
    return helper.get_page_info(page_num, total_items, page_size)