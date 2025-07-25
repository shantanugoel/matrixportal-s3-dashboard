"""
Flexible font system for MatrixPortal S3 Dashboard
Supports multiple font files, dynamic sizing, and smart text fitting
"""
from . import fonts

class FontManager:
    """Manages multiple fonts and provides smart text fitting"""
    
    def __init__(self):
        self.fonts = {}
        self._load_fonts()
    
    def _load_fonts(self):
        """Load available internal bitmap fonts"""
        self.fonts = {
            'large': fonts.FONT_5x7,
            'tiny': fonts.FONT_3x5,
        }
        print("Loaded internal bitmap fonts: large (5x7), tiny (3x5)")
    
    def get_best_font_for_text(self, text, max_width, max_height, max_lines=1, word_wrap=True):
        """
        Find the best font size to fit text in the given constraints.
        """
        font_priority = ['large', 'tiny']
        
        for font_name in font_priority:
            font_info = self.fonts[font_name]
            result = self._test_font_fit(font_info, text, max_width, max_height, max_lines, word_wrap)
            
            if result['fits']:
                result['font_name'] = font_name
                return result
        
        # If nothing fits, use the smallest font and truncate
        smallest_font_name = 'tiny'
        smallest_font = self.fonts[smallest_font_name]
        result = self._test_font_fit(smallest_font, text, max_width, max_height, max_lines, word_wrap)
        result['font_name'] = smallest_font_name
        result['fits'] = False # Mark as not an ideal fit
        return result

    def _test_font_fit(self, font_info, text, max_width, max_height, max_lines, word_wrap):
        """Test if text fits with a given bitmap font."""
        char_width = font_info['width']
        char_height = font_info['height']
        char_spacing = font_info['spacing']
        line_height = char_height + 1
        
        effective_char_width = char_width + char_spacing
        chars_per_line = max_width // effective_char_width if effective_char_width > 0 else 0

        if chars_per_line == 0:
            return {'fits': False, 'lines': [], 'font': font_info, 'font_name': None, 'char_width': 0, 'char_height': 0, 'line_height': 0}

        lines = []
        if word_wrap:
            # Word wrapping logic
            words = text.split(' ')
            current_line = ""
            for word in words:
                if len(word) > chars_per_line:
                    if current_line:
                        lines.append(current_line)
                    for i in range(0, len(word), chars_per_line):
                        lines.append(word[i:i+chars_per_line])
                    current_line = ""
                    continue

                test_line = current_line + (" " if current_line else "") + word
                if len(test_line) <= chars_per_line:
                    current_line = test_line
                else:
                    lines.append(current_line)
                    current_line = word
            
            if current_line:
                lines.append(current_line)
        else:
            # Corrected character wrapping with hyphenation
            idx = 0
            while idx < len(text):
                line = text[idx : idx + chars_per_line]
                
                if idx + chars_per_line >= len(text):
                    lines.append(line)
                    break
                
                char_after_line = text[idx + chars_per_line]
                
                if line.endswith(' ') or char_after_line == ' ':
                    lines.append(line.rstrip())
                    idx += len(line.rstrip()) + 1
                else:
                    lines.append(line[:-1] + '-')
                    idx += chars_per_line - 1

        # Check if the number of lines and total height fit
        total_height = len(lines) * line_height
        fits = len(lines) <= max_lines and total_height <= max_height

        # Truncate lines if they don't fit
        if len(lines) > max_lines:
            lines = lines[:max_lines]
            if len(lines) > 0 and not word_wrap:
                # Ensure the last line doesn't end with a hyphen if truncated
                if lines[-1].endswith('-'):
                    # This is tricky, we don't have the original char.
                    # For simplicity, just remove the hyphen.
                    lines[-1] = lines[-1][:-1]

        return {
            'fits': fits,
            'lines': lines,
            'font': font_info,
            'font_name': None,
            'char_width': char_width,
            'char_height': char_height,
            'line_height': line_height
        }

    def draw_fitted_text(self, buffer, layout, x, y, color, max_width=None, max_height=None):
        """
        Draw text using the layout from get_best_font_for_text.
        """
        try:
            font = layout['font']
            line_height = layout['line_height']
            
            for line_idx, line in enumerate(layout['lines']):
                line_y = y + (line_idx * line_height)
                
                if max_height and line_y >= (y + max_height):
                    break
                
                fonts.draw_text(buffer, line, x, line_y, color, font, max_width)
            
            return True
        except Exception as e:
            print(f"Error in draw_fitted_text: {e}")
            return False

# Global font manager instance
font_manager = FontManager()

def fit_and_draw_text(buffer, text, x, y, max_width, max_height, color, max_lines=1, word_wrap=True):
    """
    Convenience function to fit and draw text in one call.
    """
    try:
        layout = font_manager.get_best_font_for_text(text, max_width, max_height, max_lines, word_wrap)
        font_manager.draw_fitted_text(buffer, layout, x, y, color, max_width, max_height)
        return layout
    except Exception as e:
        print(f"Error in fit_and_draw_text: {e}")
        return {'fits': False, 'lines': [text], 'font': 'fallback'}