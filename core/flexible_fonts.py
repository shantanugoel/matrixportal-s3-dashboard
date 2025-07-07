"""
Flexible font system for MatrixPortal S3 Dashboard
Supports multiple font files, dynamic sizing, and smart text fitting
"""

import displayio

try:
    from adafruit_display_text import label
    from adafruit_bitmap_font import bitmap_font
    DISPLAY_TEXT_AVAILABLE = True
except ImportError:
    DISPLAY_TEXT_AVAILABLE = False
    print("adafruit_display_text not available - using fallback font system")

# Fallback to our bitmap fonts if display_text is not available
from .fonts import FONT_5x7, draw_char

class FontManager:
    """Manages multiple fonts and provides smart text fitting"""
    
    def __init__(self):
        self.fonts = {}
        self.fallback_enabled = not DISPLAY_TEXT_AVAILABLE
        
        # Load available fonts
        self._load_fonts()
    
    def _load_fonts(self):
        """Load available font files"""
        if not DISPLAY_TEXT_AVAILABLE:
            # Use our bitmap font as fallback
            self.fonts['bitmap_5x7'] = {
                'type': 'bitmap',
                'width': 5,
                'height': 7,
                'spacing': 1
            }
            return
        
        # Try to load different font files
        font_files = [
            ('small', 'fonts/font5x8.pcf'),
            ('medium', 'fonts/tom-thumb.pcf'), 
            ('large', 'fonts/6x10.pcf'),
            ('tiny', 'fonts/4x6.pcf')
        ]
        
        for name, path in font_files:
            try:
                font = bitmap_font.load_font(path)
                self.fonts[name] = {
                    'type': 'pcf',
                    'font': font,
                    'path': path
                }
                print(f"Loaded font: {name} from {path}")
            except Exception as e:
                print(f"Could not load font {name}: {e}")
        
        # Fallback to built-in if no fonts loaded
        if not self.fonts:
            print("No PCF fonts found, using bitmap fallback")
            self.fallback_enabled = True
            self.fonts['bitmap_5x7'] = {
                'type': 'bitmap', 
                'width': 5,
                'height': 7,
                'spacing': 1
            }
    
    def get_best_font_for_text(self, text, max_width, max_height, max_lines=1):
        """
        Find the best font size to fit text in the given constraints
        
        Args:
            text: Text to fit
            max_width: Maximum width in pixels
            max_height: Maximum height in pixels  
            max_lines: Maximum number of lines allowed
            
        Returns:
            dict: Font info and fitted text layout
        """
        if self.fallback_enabled:
            return self._fit_bitmap_text(text, max_width, max_height, max_lines)
        
        # Try fonts from largest to smallest
        font_priority = ['large', 'medium', 'small', 'tiny']
        
        for font_name in font_priority:
            if font_name not in self.fonts:
                continue
                
            font_info = self.fonts[font_name]
            result = self._test_font_fit(font_info, text, max_width, max_height, max_lines)
            
            if result['fits']:
                result['font_name'] = font_name
                return result
        
        # If nothing fits, use smallest font and truncate
        smallest_font = self._get_smallest_font()
        result = self._test_font_fit(smallest_font, text, max_width, max_height, max_lines)
        result['font_name'] = 'fallback'
        result['fits'] = False  # Mark as not ideal fit
        return result
    
    def _test_font_fit(self, font_info, text, max_width, max_height, max_lines):
        """Test if text fits with given font"""
        if font_info['type'] == 'bitmap':
            return self._fit_bitmap_text(text, max_width, max_height, max_lines)
        
        font = font_info['font']
        
        # Estimate character dimensions (this is approximate)
        char_width = 6  # Approximate average character width
        char_height = 8  # Approximate font height
        
        chars_per_line = max_width // char_width
        total_chars = len(text)
        needed_lines = (total_chars + chars_per_line - 1) // chars_per_line
        
        fits = needed_lines <= max_lines and (needed_lines * char_height) <= max_height
        
        # Break text into lines
        lines = []
        for i in range(0, len(text), chars_per_line):
            lines.append(text[i:i + chars_per_line])
            if len(lines) >= max_lines:
                break
        
        # Truncate last line if needed
        if len(lines) == max_lines and len(lines[-1]) > chars_per_line:
            lines[-1] = lines[-1][:chars_per_line - 3] + "..."
        
        return {
            'fits': fits,
            'lines': lines[:max_lines],
            'font': font,
            'char_width': char_width,
            'char_height': char_height,
            'line_height': char_height + 1
        }
    
    def _fit_bitmap_text(self, text, max_width, max_height, max_lines):
        """Fit text using bitmap font"""
        char_width = 5
        char_height = 7
        char_spacing = 1
        line_height = char_height + 1
        
        effective_char_width = char_width + char_spacing
        chars_per_line = max_width // effective_char_width
        
        print(f"_fit_bitmap_text: '{text}', max_width={max_width}, chars_per_line={chars_per_line}")
        
        # If single line, try to fit as much as possible
        if max_lines == 1:
            if len(text) <= chars_per_line:
                lines = [text]
                fits = True
            else:
                # Try to fit without breaking words first
                truncated = text[:chars_per_line]
                # If we cut in the middle of a word, try to cut at word boundary
                if chars_per_line > 3 and len(text) > chars_per_line:
                    words = text.split(' ')
                    current_line = ""
                    for word in words:
                        test_line = current_line + (" " if current_line else "") + word
                        if len(test_line) <= chars_per_line:
                            current_line = test_line
                        else:
                            break
                    
                    if current_line and len(current_line) >= chars_per_line - 3:
                        # Use word boundary version
                        lines = [current_line]
                    else:
                        # Use character truncation with ellipsis
                        lines = [text[:chars_per_line-3] + "..."]
                else:
                    lines = [truncated]
                fits = False
        else:
            # Multi-line text fitting
            lines = []
            words = text.split(' ')
            current_line = ""
            
            for word in words:
                test_line = current_line + (" " if current_line else "") + word
                if len(test_line) <= chars_per_line:
                    current_line = test_line
                else:
                    if current_line:
                        lines.append(current_line)
                        current_line = word[:chars_per_line]  # Start new line
                    else:
                        lines.append(word[:chars_per_line])  # Single word too long
                    
                    if len(lines) >= max_lines:
                        break
            
            if current_line and len(lines) < max_lines:
                lines.append(current_line)
            
            # Truncate to max lines
            lines = lines[:max_lines]
            
            # Add ellipsis to last line if text was truncated
            if len(lines) == max_lines and (len(' '.join(words)) > sum(len(line) for line in lines)):
                if len(lines[-1]) > 3:
                    lines[-1] = lines[-1][:-3] + "..."
            
            total_height = len(lines) * line_height
            fits = total_height <= max_height
        
        print(f"Result: chars_per_line={chars_per_line}, lines={lines}, fits={fits}")
        
        return {
            'fits': fits,
            'lines': lines,
            'font': 'bitmap',
            'char_width': char_width,
            'char_height': char_height,
            'line_height': line_height
        }
    
    def _get_smallest_font(self):
        """Get the smallest available font"""
        priority = ['tiny', 'small', 'medium', 'large', 'bitmap_5x7']
        for font_name in priority:
            if font_name in self.fonts:
                return self.fonts[font_name]
        return self.fonts['bitmap_5x7']  # Fallback
    
    def draw_fitted_text(self, buffer, layout, x, y, color, max_width=None, max_height=None):
        """
        Draw text using the layout from get_best_font_for_text
        
        Args:
            buffer: Display buffer
            layout: Result from get_best_font_for_text  
            x, y: Starting position
            color: Color index
            max_width, max_height: Optional bounds checking
        """
        if layout['font'] == 'bitmap' or self.fallback_enabled:
            return self._draw_bitmap_text(buffer, layout, x, y, color, max_width, max_height)
        else:
            return self._draw_pcf_text(buffer, layout, x, y, color, max_width, max_height)
    
    def _draw_bitmap_text(self, buffer, layout, x, y, color, max_width, max_height):
        """Draw text using bitmap font"""
        try:
            line_height = layout['line_height']
            char_width = layout['char_width']
            char_spacing = 1
            
            print(f"Drawing bitmap text: {layout['lines']} at ({x},{y})")
            
            for line_idx, line in enumerate(layout['lines']):
                line_y = y + (line_idx * line_height)
                
                print(f"Drawing line {line_idx}: '{line}' at y={line_y}")
                
                # Skip if line is out of bounds
                if max_height and line_y >= (y + max_height):
                    print(f"Line {line_idx} out of bounds: {line_y} >= {y + max_height}")
                    break
                    
                for char_idx, char in enumerate(line):
                    char_x = x + (char_idx * (char_width + char_spacing))
                    
                    # Skip if character is out of bounds
                    if max_width and char_x >= (x + max_width):
                        break
                    
                    # Draw character using bitmap font
                    if char.upper() in FONT_5x7:
                        draw_char(buffer, char.upper(), char_x, line_y, color)
            
            return True
        except Exception as e:
            print(f"Error in _draw_bitmap_text: {e}")
            return False
    
    def _draw_pcf_text(self, buffer, layout, x, y, color, max_width, max_height):
        """Draw text using PCF font (placeholder for CircuitPython implementation)"""
        # This would use adafruit_display_text.label in real CircuitPython
        # For now, fall back to bitmap
        return self._draw_bitmap_text(buffer, layout, x, y, color, max_width, max_height)

# Global font manager instance
font_manager = FontManager()

def fit_and_draw_text(buffer, text, x, y, max_width, max_height, color, max_lines=1):
    """
    Convenience function to fit and draw text in one call
    
    Args:
        buffer: Display buffer
        text: Text to draw
        x, y: Position 
        max_width, max_height: Available space
        color: Color index
        max_lines: Maximum lines allowed
        
    Returns:
        dict: Layout information used
    """
    try:
        print(f"fit_and_draw_text: '{text}' at ({x},{y}) size {max_width}x{max_height} lines={max_lines}")
        layout = font_manager.get_best_font_for_text(text, max_width, max_height, max_lines)
        print(f"Layout: {layout.get('fits', False)}, lines: {len(layout.get('lines', []))}")
        
        result = font_manager.draw_fitted_text(buffer, layout, x, y, color, max_width, max_height)
        print(f"Draw result: {result}")
        return layout
    except Exception as e:
        print(f"Error in fit_and_draw_text: {e}")
        # Fallback to simple text
        try:
            from .fonts import draw_text
            draw_text(buffer, text[:10], x, y, color, max_width)
        except:
            pass
        return {'fits': False, 'lines': [text], 'font': 'fallback'}
