from flask import request, url_for, jsonify
from dataclasses import dataclass
from typing import List, Any, Optional

@dataclass
class PaginationObject:
    """Standard pagination object for FHIR-style responses"""
    total: int
    count: int  # number of items in current page
    offset: int  # starting index (0-based)
    limit: int  # items per page
    next_url: Optional[str] = None
    previous_url: Optional[str] = None
    first_url: Optional[str] = None
    last_url: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "total": self.total,
            "count": self.count,
            "offset": self.offset,
            "limit": self.limit,
            "next": self.next_url,
            "previous": self.previous_url,
            "first": self.first_url,
            "last": self.last_url
        }


class FHIRPagination:
    """Handles pagination for FHIR endpoints"""
    
    def __init__(self, default_limit=50, max_limit=500):
        self.default_limit = default_limit
        self.max_limit = max_limit
    
    def get_pagination_params(self) -> tuple[int, int]:
        """Extract pagination params from request"""
        limit = request.args.get('_count', self.default_limit, type=int)
        offset = request.args.get('_offset', 0, type=int)        
        limit = min(limit, self.max_limit)
        offset = max(0, offset)
        
        return offset, limit
    
    def create_pagination(self, total_items: int, offset: int, limit: int, 
                         items_in_page: int, endpoint: str, resource_type: str) -> PaginationObject:
        """Create pagination object with URLs"""
        pagination = PaginationObject(
            total=total_items,
            count=items_in_page,
            offset=offset,
            limit=limit
        )
        
        # Generate URLs based on current request
        args = request.args.copy()
        
        # Next page
        if offset + limit < total_items:
            args['_offset'] = str(offset + limit)
            args['resource_type'] = resource_type
            pagination.next_url = url_for(endpoint, **args, _external=True)
        
        # Previous page
        if offset - limit >= 0:
            args['_offset'] = str(offset - limit)
            pagination.previous_url = url_for(endpoint, **args, _external=True)
        
        # First page
        if offset > 0:
            args['_offset'] = "0"
            pagination.first_url = url_for(endpoint, **args, _external=True)
        
        # Last page
        if offset + limit < total_items:
            last_offset = ((total_items - 1) // limit) * limit
            args['_offset'] = str(last_offset)
            pagination.last_url = url_for(endpoint, **args, _external=True)
        
        return pagination