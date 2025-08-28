import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import os
from PIL import Image, ImageTk, ImageDraw, ImageFont
import math

class LabelEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("Label Point Editor")
        self.root.geometry("1400x900")
        
        # Variables
        self.current_folder = ""
        self.image_json_pairs = []
        self.current_pair_index = 0
        self.current_image = None
        self.current_json_data = None
        self.display_image = None
        self.canvas_image = None
        self.scale_factor = 1.0
        
        # UI Controls variables
        self.point_size = tk.IntVar(value=8)
        self.text_size = tk.IntVar(value=12)
        self.selected_point_index = tk.IntVar(value=-1)
        self.zoom_factor = 1.0
        self.pan_start_x = 0
        self.pan_start_y = 0
        self.is_panning = False
        self.drag_threshold = 5
        
        # Text styling variables
        self.text_color = tk.StringVar(value="black")
        self.text_stroke_width = tk.IntVar(value=0)
        self.text_stroke_color = tk.StringVar(value="white")
        self.text_font_family = tk.StringVar(value="Arial")
        self.text_bold = tk.BooleanVar(value=False)  # pixels - minimum distance to start panning
        self.click_start_x = 0
        self.click_start_y = 0
        
        # Setup UI
        self.setup_ui()
        
    def setup_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Top controls frame
        controls_frame = ttk.Frame(main_frame)
        controls_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Folder selection
        ttk.Button(controls_frame, text="Select Folder", 
                  command=self.select_folder).pack(side=tk.LEFT, padx=(0, 10))
        
        # File navigation
        self.file_label = ttk.Label(controls_frame, text="No folder selected")
        self.file_label.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(controls_frame, text="Previous", 
                  command=self.previous_file).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(controls_frame, text="Next", 
                  command=self.next_file).pack(side=tk.LEFT, padx=(0, 10))
        
        # Save button
        ttk.Button(controls_frame, text="Save Changes", 
                  command=self.save_changes).pack(side=tk.RIGHT)
        
        # Content frame
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Left panel - Image display
        image_frame = ttk.LabelFrame(content_frame, text="Image with Labels")
        image_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # Canvas with scrollbars for image
        canvas_frame = ttk.Frame(image_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.canvas = tk.Canvas(canvas_frame, bg='white')
        h_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        v_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        
        self.canvas.configure(xscrollcommand=h_scrollbar.set, yscrollcommand=v_scrollbar.set)
        
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Bind canvas events
        self.canvas.bind("<ButtonPress-1>", self.start_pan_or_select)
        self.canvas.bind("<B1-Motion>", self.do_pan_or_drag)
        self.canvas.bind("<ButtonRelease-1>", self.end_pan_or_select)
        self.canvas.bind("<MouseWheel>", self.zoom)     # Mouse wheel zoom
        self.canvas.bind("<Button-4>", self.zoom)       # Linux scroll up
        self.canvas.bind("<Button-5>", self.zoom)       # Linux scroll down
        
        # Right panel - Controls and label list
        right_frame = ttk.Frame(content_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Size controls
        size_frame = ttk.LabelFrame(right_frame, text="Display Controls")
        size_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(size_frame, text="Point Size:").pack(anchor=tk.W, padx=5, pady=(5, 0))
        point_scale = ttk.Scale(size_frame, from_=3, to=20, orient=tk.HORIZONTAL, 
                               variable=self.point_size, command=self.update_display)
        point_scale.pack(fill=tk.X, padx=5)
        
        ttk.Label(size_frame, text="Text Size:").pack(anchor=tk.W, padx=5, pady=(10, 0))
        text_scale = ttk.Scale(size_frame, from_=8, to=48, orient=tk.HORIZONTAL, 
                              variable=self.text_size, command=self.update_display)
        text_scale.pack(fill=tk.X, padx=5, pady=(0, 5))
        
        # Text styling controls
        text_style_frame = ttk.LabelFrame(right_frame, text="Text Styling")
        text_style_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Font family
        ttk.Label(text_style_frame, text="Font:").pack(anchor=tk.W, padx=5, pady=(5, 0))
        font_combo = ttk.Combobox(text_style_frame, textvariable=self.text_font_family, 
                                 values=["Arial", "Times New Roman", "Courier New", "Helvetica", "Verdana"],
                                 state="readonly")
        font_combo.pack(fill=tk.X, padx=5)
        font_combo.bind("<<ComboboxSelected>>", self.update_display)
        
        # Text color
        ttk.Label(text_style_frame, text="Text Color:").pack(anchor=tk.W, padx=5, pady=(10, 0))
        color_frame = ttk.Frame(text_style_frame)
        color_frame.pack(fill=tk.X, padx=5)
        
        color_combo = ttk.Combobox(color_frame, textvariable=self.text_color,
                                  values=["black", "white", "red", "blue", "green", "yellow", "orange", "purple"],
                                  state="readonly", width=10)
        color_combo.pack(side=tk.LEFT)
        color_combo.bind("<<ComboboxSelected>>", self.update_display)
        
        # Bold checkbox
        bold_check = ttk.Checkbutton(color_frame, text="Bold", variable=self.text_bold,
                                    command=self.update_display)
        bold_check.pack(side=tk.LEFT, padx=(10, 0))
        
        # Stroke controls
        ttk.Label(text_style_frame, text="Stroke Width:").pack(anchor=tk.W, padx=5, pady=(10, 0))
        stroke_scale = ttk.Scale(text_style_frame, from_=0, to=5, orient=tk.HORIZONTAL,
                               variable=self.text_stroke_width, command=self.update_display)
        stroke_scale.pack(fill=tk.X, padx=5)
        
        ttk.Label(text_style_frame, text="Stroke Color:").pack(anchor=tk.W, padx=5, pady=(10, 0))
        stroke_combo = ttk.Combobox(text_style_frame, textvariable=self.text_stroke_color,
                                   values=["white", "black", "red", "blue", "green", "yellow", "orange", "purple"],
                                   state="readonly")
        stroke_combo.pack(fill=tk.X, padx=5, pady=(0, 5))
        stroke_combo.bind("<<ComboboxSelected>>", self.update_display)
        
        # Zoom controls
        ttk.Label(size_frame, text="Zoom:").pack(anchor=tk.W, padx=5, pady=(10, 0))
        zoom_frame = ttk.Frame(size_frame)
        zoom_frame.pack(fill=tk.X, padx=5, pady=(0, 5))
        
        ttk.Button(zoom_frame, text="Zoom In", 
                  command=self.zoom_in).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(zoom_frame, text="Zoom Out", 
                  command=self.zoom_out).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(zoom_frame, text="Fit", 
                  command=self.fit_to_canvas).pack(side=tk.LEFT)
        
        # Label list and editing
        label_frame = ttk.LabelFrame(right_frame, text="Labels")
        label_frame.pack(fill=tk.BOTH, expand=True)
        
        # Label listbox with scrollbar
        listbox_frame = ttk.Frame(label_frame)
        listbox_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.label_listbox = tk.Listbox(listbox_frame, selectmode=tk.SINGLE)
        label_scrollbar = ttk.Scrollbar(listbox_frame, orient=tk.VERTICAL, command=self.label_listbox.yview)
        self.label_listbox.configure(yscrollcommand=label_scrollbar.set)
        
        self.label_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        label_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.label_listbox.bind("<<ListboxSelect>>", self.on_label_select)
        
        # Label editing
        edit_frame = ttk.Frame(label_frame)
        edit_frame.pack(fill=tk.X, padx=5, pady=(0, 5))
        
        ttk.Label(edit_frame, text="Edit Label:").pack(anchor=tk.W)
        self.label_entry = ttk.Entry(edit_frame)
        self.label_entry.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Button(edit_frame, text="Update Label", 
                  command=self.update_label).pack(fill=tk.X)
        
        # Status bar
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.status_bar = ttk.Label(status_frame, text="Ready - Click to select points, drag to pan image", relief=tk.SUNKEN)
        self.status_bar.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Instructions label
        instructions = ttk.Label(status_frame, text="Mouse Wheel: Zoom | Left Click: Select | Left Drag: Pan", 
                                font=('TkDefaultFont', 8), foreground='gray')
        instructions.pack(side=tk.RIGHT, padx=(10, 0))
        
    def select_folder(self):
        folder = filedialog.askdirectory(title="Select folder containing images and JSON files")
        if folder:
            self.current_folder = folder
            self.load_image_json_pairs()
            if self.image_json_pairs:
                self.current_pair_index = 0
                self.load_current_pair()
            
    def load_image_json_pairs(self):
        """Find all image-JSON pairs in the selected folder"""
        self.image_json_pairs = []
        
        if not self.current_folder:
            return
            
        # Get all JSON files
        json_files = [f for f in os.listdir(self.current_folder) if f.endswith('.json')]
        
        for json_file in json_files:
            # Find corresponding image file
            base_name = os.path.splitext(json_file)[0]
            image_extensions = ['.png', '.jpg', '.jpeg', '.bmp', '.tiff']
            
            for ext in image_extensions:
                image_file = base_name + ext
                image_path = os.path.join(self.current_folder, image_file)
                
                if os.path.exists(image_path):
                    json_path = os.path.join(self.current_folder, json_file)
                    self.image_json_pairs.append({
                        'image': image_path,
                        'json': json_path,
                        'name': base_name
                    })
                    break
        
        self.update_status(f"Found {len(self.image_json_pairs)} image-JSON pairs")
        
    def load_current_pair(self):
        """Load the current image-JSON pair"""
        if not self.image_json_pairs or self.current_pair_index >= len(self.image_json_pairs):
            return
            
        pair = self.image_json_pairs[self.current_pair_index]
        
        # Update file label
        self.file_label.config(text=f"{self.current_pair_index + 1}/{len(self.image_json_pairs)}: {pair['name']}")
        
        # Load image
        try:
            self.current_image = Image.open(pair['image'])
            self.update_status(f"Loaded image: {os.path.basename(pair['image'])}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load image: {str(e)}")
            return
            
        # Load JSON
        try:
            with open(pair['json'], 'r') as f:
                self.current_json_data = json.load(f)
            self.update_status(f"Loaded JSON: {os.path.basename(pair['json'])}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load JSON: {str(e)}")
            return
            
        # Update displays
        self.zoom_factor = 1.0  # Reset zoom when loading new image
        self.update_label_list()
        self.update_display()
        
    def update_label_list(self):
        """Update the label listbox with current labels"""
        self.label_listbox.delete(0, tk.END)
        
        if not self.current_json_data or 'shapes' not in self.current_json_data:
            return
            
        for i, shape in enumerate(self.current_json_data['shapes']):
            if shape.get('shape_type') == 'point' and 'label' in shape:
                label = shape['label']
                points = shape.get('points', [])
                if points:
                    x, y = points[0]
                    self.label_listbox.insert(tk.END, f"{i:2d}: {label} ({x:.1f}, {y:.1f})")
                    
    def update_display(self, event=None):
        """Update the image display with labels"""
        if not self.current_image or not self.current_json_data:
            return
            
        # Create a copy of the image to draw on
        display_img = self.current_image.copy()
        draw = ImageDraw.Draw(display_img)
        
        # Try to create font with styling
        font = self.get_styled_font()
        
        point_radius = self.point_size.get()
        stroke_width = self.text_stroke_width.get()
        
        # Draw all points and labels
        if 'shapes' in self.current_json_data:
            for i, shape in enumerate(self.current_json_data['shapes']):
                if shape.get('shape_type') == 'point' and 'points' in shape:
                    points = shape['points']
                    if points:
                        x, y = points[0]
                        label = shape.get('label', 'Unknown')
                        
                        # Choose color based on selection
                        if i == self.selected_point_index.get():
                            point_color = 'red'
                            text_color = 'red'
                        else:
                            point_color = 'blue'
                            text_color = self.text_color.get()
                        
                        # Draw point
                        draw.ellipse([x - point_radius, y - point_radius, 
                                    x + point_radius, y + point_radius], 
                                   fill=point_color, outline='white', width=2)
                        
                        # Draw label text with stroke if enabled
                        text_x = x + point_radius + 5
                        text_y = y - point_radius
                        
                        if stroke_width > 0:
                            # Draw stroke by drawing text multiple times in different positions
                            stroke_color = self.text_stroke_color.get()
                            for adj_x in range(-stroke_width, stroke_width + 1):
                                for adj_y in range(-stroke_width, stroke_width + 1):
                                    if adj_x != 0 or adj_y != 0:
                                        draw.text((text_x + adj_x, text_y + adj_y), 
                                                label, fill=stroke_color, font=font)
                        
                        # Draw main text
                        draw.text((text_x, text_y), label, fill=text_color, font=font)
        
        # Apply zoom
        if self.zoom_factor != 1.0:
            img_width, img_height = display_img.size
            new_width = int(img_width * self.zoom_factor)
            new_height = int(img_height * self.zoom_factor)
            display_img = display_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        self.display_image = display_img
        self.canvas_image = ImageTk.PhotoImage(display_img)
        
        # Clear canvas and add image
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.canvas_image)
        
        # Update scroll region
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        
    def on_label_select(self, event):
        """Handle label listbox selection"""
        selection = self.label_listbox.curselection()
        if not selection:
            return
            
        listbox_index = selection[0]
        
        # Find the corresponding shape index
        point_index = 0
        shape_index = -1
        for i, shape in enumerate(self.current_json_data.get('shapes', [])):
            if shape.get('shape_type') == 'point':
                if point_index == listbox_index:
                    shape_index = i
                    break
                point_index += 1
        
        if shape_index >= 0:
            self.selected_point_index.set(shape_index)
            label = self.current_json_data['shapes'][shape_index].get('label', '')
            self.label_entry.delete(0, tk.END)
            self.label_entry.insert(0, label)
            self.update_display()
    
    def update_label(self):
        """Update the selected label"""
        selected_idx = self.selected_point_index.get()
        
        if selected_idx < 0 or not self.current_json_data or 'shapes' not in self.current_json_data:
            messagebox.showwarning("Warning", "No point selected")
            return
            
        if selected_idx >= len(self.current_json_data['shapes']):
            messagebox.showerror("Error", "Invalid point selection")
            return
            
        new_label = self.label_entry.get().strip()
        if not new_label:
            messagebox.showwarning("Warning", "Label cannot be empty")
            return
            
        # Update the label
        self.current_json_data['shapes'][selected_idx]['label'] = new_label
        
        # Refresh displays
        self.update_label_list()
        self.update_display()
        
        # Maintain selection
        listbox_index = 0
        for i, shape in enumerate(self.current_json_data['shapes']):
            if shape.get('shape_type') == 'point':
                if i == selected_idx:
                    self.label_listbox.selection_set(listbox_index)
                    break
                listbox_index += 1
                
        self.update_status(f"Updated label to: {new_label}")
        
    def get_styled_font(self):
        """Get a font with the current styling settings"""
        font_size = self.text_size.get()
        font_family = self.text_font_family.get()
        is_bold = self.text_bold.get()
        
        # Try different font file names based on family and style
        font_files = []
        
        if font_family == "Arial":
            if is_bold:
                font_files = ["arialbd.ttf", "Arial Bold.ttf", "arial-bold.ttf"]
            else:
                font_files = ["arial.ttf", "Arial.ttf"]
        elif font_family == "Times New Roman":
            if is_bold:
                font_files = ["timesbd.ttf", "Times New Roman Bold.ttf", "times-bold.ttf"]
            else:
                font_files = ["times.ttf", "Times New Roman.ttf"]
        elif font_family == "Courier New":
            if is_bold:
                font_files = ["courbd.ttf", "Courier New Bold.ttf", "courier-bold.ttf"]
            else:
                font_files = ["cour.ttf", "Courier New.ttf"]
        elif font_family == "Helvetica":
            if is_bold:
                font_files = ["helvetica-bold.ttf", "Helvetica-Bold.ttf"]
            else:
                font_files = ["helvetica.ttf", "Helvetica.ttf"]
        elif font_family == "Verdana":
            if is_bold:
                font_files = ["verdanab.ttf", "Verdana Bold.ttf", "verdana-bold.ttf"]
            else:
                font_files = ["verdana.ttf", "Verdana.ttf"]
        
        # Try to load the font
        for font_file in font_files:
            try:
                return ImageFont.truetype(font_file, font_size)
            except:
                continue
        
        # Fallback to default font
        try:
            return ImageFont.load_default()
        except:
            # Ultimate fallback - create a basic font
            return ImageFont.load_default()
        
    def save_changes(self):
        """Save the current JSON data"""
        if not self.current_json_data or not self.image_json_pairs:
            messagebox.showwarning("Warning", "No data to save")
            return
            
        try:
            pair = self.image_json_pairs[self.current_pair_index]
            with open(pair['json'], 'w') as f:
                json.dump(self.current_json_data, f, indent=2)
            
            self.update_status(f"Saved changes to {os.path.basename(pair['json'])}")
            messagebox.showinfo("Success", "Changes saved successfully!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save changes: {str(e)}")
    
    def previous_file(self):
        """Load previous file"""
        if self.image_json_pairs and self.current_pair_index > 0:
            self.current_pair_index -= 1
            self.load_current_pair()
            
    def next_file(self):
        """Load next file"""
        if self.image_json_pairs and self.current_pair_index < len(self.image_json_pairs) - 1:
            self.current_pair_index += 1
            self.load_current_pair()
            
    def update_status(self, message):
        """Update status bar"""
        self.status_bar.config(text=message)
    
    def zoom_in(self):
        """Zoom in by 25%"""
        old_zoom = self.zoom_factor
        self.zoom_factor *= 1.25
        if self.zoom_factor > 10.0:
            self.zoom_factor = 10.0
        
        zoom_ratio = self.zoom_factor / old_zoom
        self.update_display()
        
        # Center the zoom on the middle of the visible area
        if zoom_ratio != 1.0:
            self._center_zoom(zoom_ratio)
        
        self.update_status(f"Zoom: {self.zoom_factor:.2f}x")
    
    def zoom_out(self):
        """Zoom out by 25%"""
        old_zoom = self.zoom_factor
        self.zoom_factor /= 1.25
        if self.zoom_factor < 0.1:
            self.zoom_factor = 0.1
        
        zoom_ratio = self.zoom_factor / old_zoom
        self.update_display()
        
        # Center the zoom on the middle of the visible area
        if zoom_ratio != 1.0:
            self._center_zoom(zoom_ratio)
        
        self.update_status(f"Zoom: {self.zoom_factor:.2f}x")
    
    def _center_zoom(self, zoom_ratio):
        """Helper method to center zoom on the middle of visible area"""
        # Get canvas dimensions
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        # Get current scroll position (top-left of visible area)
        x_scroll = self.canvas.canvasx(0)
        y_scroll = self.canvas.canvasy(0)
        
        # Calculate center of visible area
        center_x = x_scroll + canvas_width / 2
        center_y = y_scroll + canvas_height / 2
        
        # Calculate new center position after zoom
        new_center_x = center_x * zoom_ratio
        new_center_y = center_y * zoom_ratio
        
        # Calculate scroll adjustment to keep center in the middle
        scroll_x = new_center_x - canvas_width / 2
        scroll_y = new_center_y - canvas_height / 2
        
        # Update scroll region
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        
        # Get the scroll region bounds
        scroll_region = self.canvas.cget("scrollregion").split()
        if len(scroll_region) == 4:
            x1, y1, x2, y2 = map(float, scroll_region)
            region_width = x2 - x1
            region_height = y2 - y1
            
            # Calculate and apply scroll fractions
            if region_width > canvas_width:
                x_fraction = scroll_x / (region_width - canvas_width)
                x_fraction = max(0, min(1, x_fraction))
                self.canvas.xview_moveto(x_fraction)
            
            if region_height > canvas_height:
                y_fraction = scroll_y / (region_height - canvas_height)
                y_fraction = max(0, min(1, y_fraction))
                self.canvas.yview_moveto(y_fraction)
    
    def fit_to_canvas(self):
        """Fit image to canvas"""
        if not self.current_image:
            return
            
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        if canvas_width > 1 and canvas_height > 1:
            img_width, img_height = self.current_image.size
            scale_x = canvas_width / img_width
            scale_y = canvas_height / img_height
            self.zoom_factor = min(scale_x, scale_y)
            self.update_display()
            self.update_status(f"Fit to canvas - Zoom: {self.zoom_factor:.2f}x")
    
    def zoom(self, event):
        """Handle mouse wheel zoom"""
        if not self.current_image:
            return
            
        # Get mouse position relative to canvas
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        
        # Get current scroll position
        x_scroll = self.canvas.canvasx(0)
        y_scroll = self.canvas.canvasy(0)
        
        # Determine zoom direction and factor
        old_zoom = self.zoom_factor
        if event.delta > 0 or event.num == 4:  # Zoom in
            self.zoom_factor *= 1.2
        else:  # Zoom out
            self.zoom_factor /= 1.2
        
        # Limit zoom range
        if self.zoom_factor < 0.1:
            self.zoom_factor = 0.1
        elif self.zoom_factor > 10.0:
            self.zoom_factor = 10.0
        
        # Calculate zoom ratio
        zoom_ratio = self.zoom_factor / old_zoom
        
        # Update the image display
        self.update_display()
        
        # Calculate new scroll position to keep mouse point centered
        if zoom_ratio != 1.0:
            # Calculate the position of the mouse relative to the image
            mouse_x_on_image = canvas_x - x_scroll
            mouse_y_on_image = canvas_y - y_scroll
            
            # Calculate new positions after zoom
            new_mouse_x = mouse_x_on_image * zoom_ratio
            new_mouse_y = mouse_y_on_image * zoom_ratio
            
            # Calculate how much to scroll to keep the mouse point in the same place
            scroll_x = new_mouse_x - mouse_x_on_image
            scroll_y = new_mouse_y - mouse_y_on_image
            
            # Get canvas dimensions
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            
            # Update scroll region first
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            
            # Get the scroll region bounds
            scroll_region = self.canvas.cget("scrollregion").split()
            if len(scroll_region) == 4:
                x1, y1, x2, y2 = map(float, scroll_region)
                region_width = x2 - x1
                region_height = y2 - y1
                
                # Calculate scroll fractions
                if region_width > canvas_width:
                    x_fraction = (x_scroll + scroll_x) / (region_width - canvas_width)
                    x_fraction = max(0, min(1, x_fraction))
                    self.canvas.xview_moveto(x_fraction)
                
                if region_height > canvas_height:
                    y_fraction = (y_scroll + scroll_y) / (region_height - canvas_height)
                    y_fraction = max(0, min(1, y_fraction))
                    self.canvas.yview_moveto(y_fraction)
        
        self.update_status(f"Zoom: {self.zoom_factor:.2f}x")
    
    def start_pan_or_select(self, event):
        """Start either panning or point selection"""
        self.is_panning = False
        self.click_start_x = event.x
        self.click_start_y = event.y
        self.pan_start_x = self.canvas.canvasx(event.x)
        self.pan_start_y = self.canvas.canvasy(event.y)
        
    def do_pan_or_drag(self, event):
        """Handle dragging - either pan the image or prepare for selection"""
        # Calculate distance moved
        dx = abs(event.x - self.click_start_x)
        dy = abs(event.y - self.click_start_y)
        distance = (dx*dx + dy*dy)**0.5
        
        # If we've moved beyond threshold, start panning
        if distance > self.drag_threshold:
            self.is_panning = True
            
            # Pan the canvas
            current_x = self.canvas.canvasx(event.x)
            current_y = self.canvas.canvasy(event.y)
            
            # Calculate movement
            dx = self.pan_start_x - current_x
            dy = self.pan_start_y - current_y
            
            # Move the canvas view
            self.canvas.scan_mark(int(self.pan_start_x), int(self.pan_start_y))
            self.canvas.scan_dragto(int(current_x), int(current_y), gain=1)
            
    def end_pan_or_select(self, event):
        """End panning or perform point selection"""
        if not self.is_panning:
            # This was a click, not a drag - handle point selection
            self.handle_point_selection(event)
        
        # Reset panning state
        self.is_panning = False
        
    def handle_point_selection(self, event):
        """Handle point selection on click (when not panning)"""
        if not self.current_json_data or 'shapes' not in self.current_json_data:
            return
            
        # Convert canvas coordinates to image coordinates
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        
        # Account for zoom
        img_x = canvas_x / self.zoom_factor if self.zoom_factor > 0 else canvas_x
        img_y = canvas_y / self.zoom_factor if self.zoom_factor > 0 else canvas_y
        
        # Find closest point
        closest_index = -1
        min_distance = float('inf')
        click_threshold = 30  # pixels
        
        for i, shape in enumerate(self.current_json_data['shapes']):
            if shape.get('shape_type') == 'point' and 'points' in shape:
                points = shape['points']
                if points:
                    x, y = points[0]
                    distance = math.sqrt((img_x - x)**2 + (img_y - y)**2)
                    
                    if distance < min_distance and distance < click_threshold:
                        min_distance = distance
                        closest_index = i
        
        # Select the closest point
        if closest_index >= 0:
            self.selected_point_index.set(closest_index)
            self.label_listbox.selection_clear(0, tk.END)
            
            # Find the corresponding listbox item
            listbox_index = 0
            for i, shape in enumerate(self.current_json_data['shapes']):
                if shape.get('shape_type') == 'point':
                    if i == closest_index:
                        self.label_listbox.selection_set(listbox_index)
                        self.label_listbox.see(listbox_index)
                        break
                    listbox_index += 1
            
            # Update entry field
            label = self.current_json_data['shapes'][closest_index].get('label', '')
            self.label_entry.delete(0, tk.END)
            self.label_entry.insert(0, label)
            
            self.update_display()

def main():
    root = tk.Tk()
    app = LabelEditor(root)
    root.mainloop()

if __name__ == "__main__":
    main()
