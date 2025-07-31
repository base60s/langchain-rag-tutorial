"""
XML parser for extracting balance sheet data from XML and XBRL files.
"""
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from uuid import uuid4
import re

try:
    import xml.etree.ElementTree as ET
    from xml.dom import minidom
    import xmltodict
except ImportError as e:
    logging.warning(f"XML parsing dependencies not available: {e}")

from .base_parser import BaseParser, ParsingResult
from ..models.document import DocumentMetadata, DocumentChunk, DocumentFormat


class XMLParser(BaseParser):
    """Parser for XML and XBRL financial documents."""
    
    def __init__(self):
        super().__init__()
        self.supported_formats = [DocumentFormat.XML, DocumentFormat.XBRL]
        self.logger = logging.getLogger(__name__)
        self._setup_xbrl_namespaces()
    
    def _setup_xbrl_namespaces(self):
        """Setup common XBRL namespaces for financial data extraction."""
        self.xbrl_namespaces = {
            'xbrl': 'http://www.xbrl.org/2003/instance',
            'us-gaap': 'http://fasb.org/us-gaap/2023',  # US GAAP taxonomy
            'dei': 'http://xbrl.sec.gov/dei/2023',  # Document and Entity Information
            'ifrs': 'http://xbrl.ifrs.org/taxonomy/2023-03-23/ifrs-full',  # IFRS taxonomy
            'link': 'http://www.xbrl.org/2003/linkbase',
            'xlink': 'http://www.w3.org/1999/xlink',
            'iso4217': 'http://www.xbrl.org/2003/iso4217',
        }
        
        # Common XBRL balance sheet elements
        self.balance_sheet_elements = {
            # Assets
            'Assets': ['Assets', 'us-gaap:Assets'],
            'CurrentAssets': ['AssetsCurrent', 'us-gaap:AssetsCurrent'],
            'CashAndCashEquivalents': ['CashAndCashEquivalentsAtCarryingValue', 'us-gaap:CashAndCashEquivalentsAtCarryingValue'],
            'AccountsReceivable': ['AccountsReceivableNetCurrent', 'us-gaap:AccountsReceivableNetCurrent'],
            'Inventory': ['InventoryNet', 'us-gaap:InventoryNet'],
            'PropertyPlantEquipment': ['PropertyPlantAndEquipmentNet', 'us-gaap:PropertyPlantAndEquipmentNet'],
            
            # Liabilities
            'Liabilities': ['Liabilities', 'us-gaap:Liabilities'],
            'CurrentLiabilities': ['LiabilitiesCurrent', 'us-gaap:LiabilitiesCurrent'],
            'AccountsPayable': ['AccountsPayableCurrent', 'us-gaap:AccountsPayableCurrent'],
            'LongTermDebt': ['LongTermDebtNoncurrent', 'us-gaap:LongTermDebtNoncurrent'],
            
            # Equity
            'StockholdersEquity': ['StockholdersEquity', 'us-gaap:StockholdersEquity'],
            'RetainedEarnings': ['RetainedEarningsAccumulatedDeficit', 'us-gaap:RetainedEarningsAccumulatedDeficit'],
        }
    
    def can_parse(self, file_path: Path) -> bool:
        """Check if this parser can handle the given XML/XBRL file."""
        return file_path.suffix.lower() in ['.xml', '.xbrl']
    
    def parse(self, file_path: Path, metadata: Optional[DocumentMetadata] = None) -> ParsingResult:
        """Parse XML/XBRL document and extract financial data."""
        try:
            result = ParsingResult(success=False)
            
            # Parse XML structure
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # Determine if this is XBRL or regular XML
            is_xbrl = self._is_xbrl_document(root)
            
            if is_xbrl:
                parsed_data = self._parse_xbrl(root, file_path)
            else:
                parsed_data = self._parse_regular_xml(root, file_path)
            
            # Convert XML structure to text for chunk creation
            xml_text = self._xml_to_text(root)
            
            # Create chunks
            text_chunks = self._split_into_chunks(xml_text)
            chunks = []
            for i, chunk_text in enumerate(text_chunks):
                chunk = DocumentChunk(
                    document_id=uuid4(),
                    chunk_index=i,
                    text=chunk_text,
                    section_type="xml_data" if not is_xbrl else "xbrl_data",
                    financial_figures=self.extract_financial_figures(chunk_text)
                )
                chunks.append(chunk)
            
            # Extract financial figures
            all_figures = self.extract_financial_figures(xml_text)
            
            result.success = True
            result.chunks = chunks
            result.tables = parsed_data.get('tables', [])
            result.figures = all_figures
            result.metadata = {
                'is_xbrl': is_xbrl,
                'document_type': 'xbrl' if is_xbrl else 'xml',
                'namespaces': dict(root.attrib) if hasattr(root, 'attrib') else {},
                'balance_sheet_data': parsed_data.get('balance_sheet_data'),
                'entity_info': parsed_data.get('entity_info'),
                'reporting_period': parsed_data.get('reporting_period'),
                'scale': self.detect_scale(xml_text)
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error parsing XML/XBRL {file_path}: {str(e)}")
            return ParsingResult(
                success=False,
                errors=[f"XML/XBRL parsing failed: {str(e)}"]
            )
    
    def _is_xbrl_document(self, root: ET.Element) -> bool:
        """Determine if the XML document is an XBRL document."""
        # Check for XBRL namespace
        if 'xbrl' in str(root.tag).lower():
            return True
        
        # Check namespace declarations
        if hasattr(root, 'attrib'):
            for attr, value in root.attrib.items():
                if 'xbrl' in attr.lower() or 'xbrl' in value.lower():
                    return True
        
        # Check for common XBRL elements
        for child in root:
            if any(term in str(child.tag).lower() for term in ['context', 'unit', 'schemaref']):
                return True
        
        return False
    
    def _parse_xbrl(self, root: ET.Element, file_path: Path) -> Dict[str, Any]:
        """Parse XBRL document to extract structured financial data."""
        parsed_data = {
            'balance_sheet_data': {'assets': [], 'liabilities': [], 'equity': []},
            'entity_info': {},
            'reporting_period': {},
            'tables': [],
            'contexts': {},
            'units': {}
        }
        
        # Extract contexts (time periods and entity information)
        contexts = self._extract_xbrl_contexts(root)
        parsed_data['contexts'] = contexts
        
        # Extract units (currencies)
        units = self._extract_xbrl_units(root)
        parsed_data['units'] = units
        
        # Extract entity information
        entity_info = self._extract_entity_info(root, contexts)
        parsed_data['entity_info'] = entity_info
        
        # Extract balance sheet facts
        balance_sheet_facts = self._extract_balance_sheet_facts(root, contexts, units)
        parsed_data['balance_sheet_data'] = balance_sheet_facts
        
        # Create table representation
        if balance_sheet_facts:
            table = self._create_balance_sheet_table(balance_sheet_facts, entity_info)
            if table:
                parsed_data['tables'].append(table)
        
        return parsed_data
    
    def _parse_regular_xml(self, root: ET.Element, file_path: Path) -> Dict[str, Any]:
        """Parse regular XML document looking for financial data patterns."""
        parsed_data = {
            'balance_sheet_data': {'assets': [], 'liabilities': [], 'equity': []},
            'tables': [],
            'structure': {}
        }
        
        # Convert XML to dictionary for easier processing
        try:
            xml_dict = xmltodict.parse(ET.tostring(root))
            parsed_data['structure'] = xml_dict
        except:
            pass
        
        # Look for financial data patterns in the XML structure
        financial_elements = self._find_financial_elements(root)
        
        # Categorize found elements
        for element in financial_elements:
            category = self._categorize_xml_element(element)
            item_data = {
                'name': element.get('name', element.tag),
                'value': element.get('value', element.text),
                'attributes': dict(element.attrib) if hasattr(element, 'attrib') else {},
                'tag': element.tag
            }
            
            if category.startswith('asset_'):
                parsed_data['balance_sheet_data']['assets'].append(item_data)
            elif category.startswith('liability_'):
                parsed_data['balance_sheet_data']['liabilities'].append(item_data)
            elif category.startswith('equity_'):
                parsed_data['balance_sheet_data']['equity'].append(item_data)
        
        return parsed_data
    
    def _extract_xbrl_contexts(self, root: ET.Element) -> Dict[str, Any]:
        """Extract XBRL contexts (time periods and entities)."""
        contexts = {}
        
        # Look for context elements
        for context in root.findall('.//xbrl:context', self.xbrl_namespaces):
            context_id = context.get('id')
            if context_id:
                context_data = {
                    'id': context_id,
                    'entity': {},
                    'period': {}
                }
                
                # Extract entity information
                entity = context.find('.//xbrl:entity', self.xbrl_namespaces)
                if entity is not None:
                    identifier = entity.find('.//xbrl:identifier', self.xbrl_namespaces)
                    if identifier is not None:
                        context_data['entity'] = {
                            'scheme': identifier.get('scheme'),
                            'value': identifier.text
                        }
                
                # Extract period information
                period = context.find('.//xbrl:period', self.xbrl_namespaces)
                if period is not None:
                    instant = period.find('.//xbrl:instant', self.xbrl_namespaces)
                    if instant is not None:
                        context_data['period']['instant'] = instant.text
                    else:
                        start_date = period.find('.//xbrl:startDate', self.xbrl_namespaces)
                        end_date = period.find('.//xbrl:endDate', self.xbrl_namespaces)
                        if start_date is not None and end_date is not None:
                            context_data['period']['start'] = start_date.text
                            context_data['period']['end'] = end_date.text
                
                contexts[context_id] = context_data
        
        return contexts
    
    def _extract_xbrl_units(self, root: ET.Element) -> Dict[str, Any]:
        """Extract XBRL units (currencies and measures)."""
        units = {}
        
        for unit in root.findall('.//xbrl:unit', self.xbrl_namespaces):
            unit_id = unit.get('id')
            if unit_id:
                measure = unit.find('.//xbrl:measure', self.xbrl_namespaces)
                if measure is not None:
                    units[unit_id] = {
                        'id': unit_id,
                        'measure': measure.text
                    }
        
        return units
    
    def _extract_entity_info(self, root: ET.Element, contexts: Dict[str, Any]) -> Dict[str, Any]:
        """Extract entity information from XBRL document."""
        entity_info = {}
        
        # Look for common entity identification elements
        entity_elements = [
            'EntityRegistrantName',
            'EntityCentralIndexKey',
            'TradingSymbol',
            'EntityFilerCategory'
        ]
        
        for element_name in entity_elements:
            # Try with dei namespace
            element = root.find(f'.//dei:{element_name}', self.xbrl_namespaces)
            if element is not None:
                entity_info[element_name] = element.text
        
        return entity_info
    
    def _extract_balance_sheet_facts(self, root: ET.Element, contexts: Dict[str, Any], units: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        """Extract balance sheet facts from XBRL document."""
        balance_sheet_data = {
            'assets': [],
            'liabilities': [],
            'equity': []
        }
        
        # Look for balance sheet elements
        for category, element_names in self.balance_sheet_elements.items():
            for element_name in element_names:
                # Try to find elements with and without namespace prefix
                elements = root.findall(f'.//{element_name}') + root.findall(f'.//us-gaap:{element_name}', self.xbrl_namespaces)
                
                for element in elements:
                    fact_data = {
                        'name': element_name,
                        'value': element.text,
                        'context_ref': element.get('contextRef'),
                        'unit_ref': element.get('unitRef'),
                        'decimals': element.get('decimals'),
                        'scale': element.get('scale')
                    }
                    
                    # Add context and unit information
                    if fact_data['context_ref'] in contexts:
                        fact_data['context'] = contexts[fact_data['context_ref']]
                    
                    if fact_data['unit_ref'] in units:
                        fact_data['unit'] = units[fact_data['unit_ref']]
                    
                    # Categorize the fact
                    if any(term in category.lower() for term in ['asset', 'cash', 'receivable', 'inventory', 'property']):
                        balance_sheet_data['assets'].append(fact_data)
                    elif any(term in category.lower() for term in ['liability', 'payable', 'debt']):
                        balance_sheet_data['liabilities'].append(fact_data)
                    elif any(term in category.lower() for term in ['equity', 'stockholder', 'retained']):
                        balance_sheet_data['equity'].append(fact_data)
        
        return balance_sheet_data
    
    def _create_balance_sheet_table(self, balance_sheet_facts: Dict[str, List[Dict[str, Any]]], entity_info: Dict[str, Any]) -> Dict[str, Any]:
        """Create a table representation of balance sheet data."""
        table = {
            'headers': ['Line Item', 'Amount', 'Context', 'Unit'],
            'rows': [],
            'is_financial': True,
            'financial_data': {
                'line_items': [],
                'entity_info': entity_info,
                'currency': 'USD',
                'scale': 'units'
            }
        }
        
        # Add assets
        for asset in balance_sheet_facts.get('assets', []):
            row = [
                asset.get('name', ''),
                asset.get('value', ''),
                asset.get('context_ref', ''),
                asset.get('unit_ref', '')
            ]
            table['rows'].append(row)
            
            table['financial_data']['line_items'].append({
                'name': asset.get('name', ''),
                'category': 'asset',
                'amount': asset.get('value', ''),
                'context': asset.get('context'),
                'unit': asset.get('unit')
            })
        
        # Add liabilities
        for liability in balance_sheet_facts.get('liabilities', []):
            row = [
                liability.get('name', ''),
                liability.get('value', ''),
                liability.get('context_ref', ''),
                liability.get('unit_ref', '')
            ]
            table['rows'].append(row)
            
            table['financial_data']['line_items'].append({
                'name': liability.get('name', ''),
                'category': 'liability',
                'amount': liability.get('value', ''),
                'context': liability.get('context'),
                'unit': liability.get('unit')
            })
        
        # Add equity
        for equity in balance_sheet_facts.get('equity', []):
            row = [
                equity.get('name', ''),
                equity.get('value', ''),
                equity.get('context_ref', ''),
                equity.get('unit_ref', '')
            ]
            table['rows'].append(row)
            
            table['financial_data']['line_items'].append({
                'name': equity.get('name', ''),
                'category': 'equity',
                'amount': equity.get('value', ''),
                'context': equity.get('context'),
                'unit': equity.get('unit')
            })
        
        table['row_count'] = len(table['rows'])
        table['column_count'] = len(table['headers'])
        
        return table
    
    def _find_financial_elements(self, root: ET.Element) -> List[ET.Element]:
        """Find elements that might contain financial data."""
        financial_elements = []
        
        # Look for elements with financial keywords in tag names
        financial_keywords = [
            'asset', 'liability', 'equity', 'cash', 'receivable', 'inventory',
            'payable', 'debt', 'capital', 'earnings', 'balance'
        ]
        
        for element in root.iter():
            tag_lower = str(element.tag).lower()
            if any(keyword in tag_lower for keyword in financial_keywords):
                financial_elements.append(element)
            
            # Also check text content for financial patterns
            if element.text and self.extract_financial_figures(element.text):
                financial_elements.append(element)
        
        return financial_elements
    
    def _categorize_xml_element(self, element: ET.Element) -> str:
        """Categorize XML element as asset, liability, or equity."""
        element_name = str(element.tag).lower()
        element_text = (element.text or '').lower()
        
        # Check against our patterns
        for category, patterns in self.asset_patterns.items():
            for pattern in patterns:
                if re.search(pattern, element_name) or re.search(pattern, element_text):
                    return f"asset_{category.value}"
        
        for category, patterns in self.liability_patterns.items():
            for pattern in patterns:
                if re.search(pattern, element_name) or re.search(pattern, element_text):
                    return f"liability_{category.value}"
        
        for category, patterns in self.equity_patterns.items():
            for pattern in patterns:
                if re.search(pattern, element_name) or re.search(pattern, element_text):
                    return f"equity_{category.value}"
        
        # General categorization
        if any(term in element_name for term in ['asset', 'cash', 'receivable', 'inventory']):
            return "asset_other"
        elif any(term in element_name for term in ['liability', 'payable', 'debt']):
            return "liability_other"
        elif any(term in element_name for term in ['equity', 'capital', 'earnings']):
            return "equity_other"
        else:
            return "unknown"
    
    def _xml_to_text(self, root: ET.Element) -> str:
        """Convert XML structure to readable text."""
        def element_to_text(element, level=0):
            indent = "  " * level
            lines = []
            
            # Add element name
            lines.append(f"{indent}{element.tag}")
            
            # Add attributes
            if hasattr(element, 'attrib') and element.attrib:
                for attr, value in element.attrib.items():
                    lines.append(f"{indent}  @{attr}: {value}")
            
            # Add text content
            if element.text and element.text.strip():
                lines.append(f"{indent}  {element.text.strip()}")
            
            # Add children
            for child in element:
                lines.extend(element_to_text(child, level + 1))
            
            return lines
        
        text_lines = element_to_text(root)
        return '\n'.join(text_lines)