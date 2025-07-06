"""
Display engine for MatrixPortal S3 Dashboard
Handles RGB LED matrix display with double buffering and PSRAM optimization
"""
import board
import displayio
import framebufferio
import rgbmatrix
import terminalio
from adafruit_display_text import bitmap_label
import gc

class DisplayEngine:
    """Manages RGB LED matrix display with double buffering"""
    
    def __init__(self, width=64, height=64, bit_depth=6):
        self.width = width
        self.height = height
        self.bit_depth = bit_depth
        
        # Display objects
        self.matrix = None
        self.display = None
        self.group = None
        
        # Double buffering
        self.front_buffer = None
        self.back_buffer = None
        self.current_buffer = None
        
        # Color palette
        self.palette = None
        
        # Initialize display
        self._init_display()
        self._init_buffers()
        
        # Clear display on startup
        self.clear()
        self.update()
        
        print(f"Display engine initialized: {width}x{height}, {bit_depth}-bit")
    
    def _init_display(self):
        """Initialize the RGB LED matrix display"""
        try:
            # Release any existing displays
            displayio.release_displays()
            
            # Configure matrix
            self.matrix = rgbmatrix.RGBMatrix(
                width=self.width,
                height=self.height,
                bit_depth=self.bit_depth,
                rgb_pins=[
                    board.MTX_R1, board.MTX_G1, board.MTX_B1,
                    board.MTX_R2, board.MTX_G2, board.MTX_B2
                ],
                addr_pins=[
                    board.MTX_ADDRA, board.MTX_ADDRB, board.MTX_ADDRC,
                    board.MTX_ADDRD, board.MTX_ADDRE
                ],
                clock_pin=board.MTX_CLK,
                latch_pin=board.MTX_LAT,
                output_enable_pin=board.MTX_OE
            )
            
            # Create display
            self.display = framebufferio.FramebufferDisplay(
                self.matrix,
                auto_refresh=False  # Manual refresh for smooth updates
            )
            
            # Create main group
            self.group = displayio.Group()
            self.display.root_group = self.group
            
        except Exception as e:
            print(f"Display initialization error: {e}")
            raise
    
    def _init_buffers(self):
        """Initialize double buffering with PSRAM"""
        try:
            # Create color palette (256 colors)
            self.palette = displayio.Palette(256)
            self._setup_palette()
            
            # Try to allocate buffers in PSRAM
            try:
                # Front buffer (currently displayed)
                self.front_buffer = displayio.Bitmap(
                    self.width, self.height, 256
                )
                
                # Back buffer (being drawn to)
                self.back_buffer = displayio.Bitmap(
                    self.width, self.height, 256
                )
                
                print("Buffers allocated in main memory")
                
            except MemoryError:
                print("Failed to allocate display buffers")
                raise
            
            # Set current buffer to back buffer
            self.current_buffer = self.back_buffer
            
            # Create TileGrid for display
            self.tile_grid = displayio.TileGrid(
                self.front_buffer,
                pixel_shader=self.palette
            )
            self.group.append(self.tile_grid)
            
        except Exception as e:
            print(f"Buffer initialization error: {e}")
            raise
    
    def _setup_palette(self):
        """Setup color palette for efficient color mapping"""
        # Basic colors (0-15)
        colors = [
            0x000000,  # 0: Black
            0xFFFFFF,  # 1: White
            0xFF0000,  # 2: Red
            0x00FF00,  # 3: Green
            0x0000FF,  # 4: Blue
            0xFFFF00,  # 5: Yellow
            0xFF00FF,  # 6: Magenta
            0x00FFFF,  # 7: Cyan
            0xFF8000,  # 8: Orange
            0x8000FF,  # 9: Purple
            0x808080,  # 10: Gray
            0x404040,  # 11: Dark Gray
            0xC0C0C0,  # 12: Light Gray
            0x800000,  # 13: Dark Red
            0x008000,  # 14: Dark Green
            0x000080,  # 15: Dark Blue
        ]
        
        # Set basic colors
        for i, color in enumerate(colors):
            self.palette[i] = color
        
        # Generate gradient colors (16-255)
        for i in range(16, 256):
            # Create RGB gradients
            r = (i - 16) * 4 % 256
            g = ((i - 16) * 7) % 256
            b = ((i - 16) * 11) % 256
            self.palette[i] = (r << 16) | (g << 8) | b
    
    def clear(self, color=0):
        """Clear the current buffer"""
        if self.current_buffer:
            self.current_buffer.fill(color)
    
    def get_buffer(self):
        """Get the current drawing buffer"""
        return self.current_buffer
    
    def get_dimensions(self):
        """Get display dimensions"""
        return (self.width, self.height)
    
    def swap_buffers(self):
        """Swap front and back buffers"""
        self.front_buffer, self.back_buffer = self.back_buffer, self.front_buffer
        self.current_buffer = self.back_buffer
        
        # Update TileGrid to show new front buffer
        self.tile_grid.bitmap = self.front_buffer
    
    def update(self):
        """Update the display with current buffer"""
        try:
            # Swap buffers
            self.swap_buffers()
            
            # Refresh display
            self.display.refresh()
            
        except Exception as e:
            print(f"Display update error: {e}")
    
    def set_pixel(self, x, y, color):
        """Set a single pixel in the current buffer"""
        if 0 <= x < self.width and 0 <= y < self.height:
            self.current_buffer[x, y] = color
    
    def draw_line(self, x0, y0, x1, y1, color):
        """Draw a line using Bresenham's algorithm"""
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        
        err = dx - dy
        
        while True:
            self.set_pixel(x0, y0, color)
            
            if x0 == x1 and y0 == y1:
                break
                
            e2 = 2 * err
            
            if e2 > -dy:
                err -= dy
                x0 += sx
            
            if e2 < dx:
                err += dx
                y0 += sy
    
    def draw_rect(self, x, y, width, height, color, filled=False):
        """Draw a rectangle"""
        if filled:
            for py in range(y, y + height):
                for px in range(x, x + width):
                    self.set_pixel(px, py, color)
        else:
            # Top and bottom edges
            for px in range(x, x + width):
                self.set_pixel(px, y, color)
                self.set_pixel(px, y + height - 1, color)
            
            # Left and right edges
            for py in range(y, y + height):
                self.set_pixel(x, py, color)
                self.set_pixel(x + width - 1, py, color)
    
    def draw_text(self, text, x, y, color=1, font=None):
        """Draw text at specified position"""
        if font is None:
            font = terminalio.FONT
        
        # Create text label
        label = bitmap_label.Label(
            font,
            text=text,
            color=self.palette[color],
            x=x,
            y=y
        )
        
        # This is a simplified approach - in practice, you'd want to
        # render the text to your bitmap buffer
        return label
    
    def scroll_text(self, text, y, color=1, speed=1):
        """Scroll text horizontally across the display"""
        # This would be implemented with a proper scrolling mechanism
        # For now, just a placeholder
        pass
    
    def set_brightness(self, brightness):
        """Set display brightness (0.0 to 1.0)"""
        if hasattr(self.display, 'brightness'):
            self.display.brightness = max(0.0, min(1.0, brightness))
    
    def get_palette_color(self, index):
        """Get color from palette"""
        if 0 <= index < len(self.palette):
            return self.palette[index]
        return 0
    
    def find_color_index(self, rgb_color):
        """Find closest color index in palette"""
        # Simple approach - find exact match or return closest
        for i, color in enumerate(self.palette):
            if color == rgb_color:
                return i
        
        # If no exact match, return closest basic color
        return self._find_closest_color(rgb_color)
    
    def _find_closest_color(self, target_color):
        """Find closest color in basic palette"""
        target_r = (target_color >> 16) & 0xFF
        target_g = (target_color >> 8) & 0xFF
        target_b = target_color & 0xFF
        
        min_distance = float('inf')
        closest_index = 0
        
        # Check first 16 colors only for performance
        for i in range(min(16, len(self.palette))):
            color = self.palette[i]
            r = (color >> 16) & 0xFF
            g = (color >> 8) & 0xFF
            b = color & 0xFF
            
            # Calculate Euclidean distance
            distance = ((r - target_r) ** 2 + (g - target_g) ** 2 + (b - target_b) ** 2) ** 0.5
            
            if distance < min_distance:
                min_distance = distance
                closest_index = i
        
        return closest_index
    
    def cleanup(self):
        """Clean up display resources"""
        try:
            if self.display:
                self.display.auto_refresh = False
                
            # Clear buffers
            if self.front_buffer:
                self.front_buffer = None
            if self.back_buffer:
                self.back_buffer = None
                
            # Force garbage collection
            gc.collect()
            
        except Exception as e:
            print(f"Display cleanup error: {e}")
