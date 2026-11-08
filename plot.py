import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, ConnectionPatch
from element import Element
from intbase import InterpreterBase

def plot_ast(ast_root, figsize=None):
    """
    Plot an AST structure showing each node as a box with its type and fields.
    
    Args:
        ast_root: Root Element of the AST
        figsize: Tuple of (width, height) for the figure. If None, will be calculated dynamically.
    """
    # Track node positions while laying out the tree.
    node_positions = {}
    node_x_padding = 0.18
    list_bracket_pad = 0.16
    list_cell_gap = 0.04
    list_cell_height = 0.24

    def truncate_label(value, max_chars):
        """Return a compact label that fits in a small plot cell."""
        label = str(value)
        if len(label) > max_chars:
            return label[:max_chars - 3] + "..."
        return label

    def list_item_label(value):
        """Prefer useful labels for list items instead of anonymous pointers."""
        if isinstance(value, Element):
            return value.elem_type
        return truncate_label(value, 9)

    def list_item_width(value):
        label = list_item_label(value)
        return min(max(0.58, len(label) * 0.075 + 0.28), 1.1)

    def list_item_specs(values):
        return [(value, list_item_label(value), list_item_width(value)) for value in values]

    def calculate_list_width(values):
        if len(values) == 0:
            return 0.72
        specs = list_item_specs(values)
        cells_width = sum(width for _, _, width in specs)
        gaps_width = list_cell_gap * (len(specs) - 1)
        return list_bracket_pad * 2 + cells_width + gaps_width

    def field_label_width(field_name):
        return min(max(0.65, len(field_name) * 0.08 + 0.18), 1.6)

    def calculate_field_width(field_name, field_value):
        if isinstance(field_value, list):
            content_width = calculate_list_width(field_value)
        elif isinstance(field_value, Element):
            content_width = 0.62
        else:
            content_width = 0.68
        return max(0.85, field_label_width(field_name), content_width + 0.08)

    def calculate_field_widths(node):
        return [
            calculate_field_width(field_name, field_value)
            for field_name, field_value in node.dict.items()
        ]
    
    def calculate_node_width(node):
        """Calculate the width needed for a node based on its fields and array contents"""
        if len(node.dict) == 0:
            return 1.8

        return max(1.8, sum(calculate_field_widths(node)) + node_x_padding * 2)
    
    def layout_tree(node, x, y, level=0, min_spacing=1.2):
        """Recursively layout the tree and collect node positions with compact spacing"""
        if node is None:
            return 0, 0
        
        # Calculate width needed for this node
        node_width = calculate_node_width(node)
        
        # Calculate width needed for this subtree
        total_width = 0
        # Process all fields
        for field_value in node.dict.values():
            if isinstance(field_value, Element):
                # Single child node
                child_width, _ = layout_tree(field_value, x + total_width, y - 1.2, level + 1, min_spacing)
                total_width += max(child_width, min_spacing)
            elif isinstance(field_value, list):
                # Array of child nodes
                for child in field_value:  # Show all items
                    if isinstance(child, Element):
                        child_width, _ = layout_tree(child, x + total_width, y - 1.2, level + 1, min_spacing)
                        total_width += max(child_width, min_spacing)
            else:
                # Primitive value (string, int, bool)
                total_width += 1.0
        
        # Ensure minimum width for the node itself
        total_width = max(total_width, node_width + 0.5)
        
        # Store node position
        node_positions[node] = (x + total_width/2, y)

        return total_width, 1
    
    # Layout the tree with compact spacing
    tree_width, _ = layout_tree(ast_root, 0, 9, min_spacing=1.2)
    
    # Calculate dynamic figure size based on tree width
    if figsize is None:
        # Add padding and ensure minimum size
        required_width = max(15, tree_width + 2)  # Add 2 units of padding
        figsize = (required_width, 10)
    
    fig, ax = plt.subplots(figsize=figsize)
    
    # Set x-axis limits based on tree width
    ax.set_xlim(-1, tree_width + 1)  # Add 1 unit padding on each side
    ax.set_ylim(0, 10)
    ax.axis('off')

    # Finalize the axes layout *before* drawing any text so the data->pixel
    # mapping is stable. fit_text() relies on this mapping to size labels.
    ax.set_title("AST Visualization", fontsize=14, fontweight='bold')
    fig.tight_layout()
    fig.canvas.draw()
    try:
        renderer = fig.canvas.get_renderer()
    except AttributeError:
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        renderer = FigureCanvasAgg(fig).get_renderer()

    def data_width_to_px(width):
        """Convert a width in data coordinates to pixels."""
        x0 = ax.transData.transform((0, 0))[0]
        x1 = ax.transData.transform((width, 0))[0]
        return abs(x1 - x0)

    def fit_text(x, y, s, max_width, fontsize, **kwargs):
        """Draw text, shrinking the font until it fits within max_width (data units)."""
        txt = ax.text(x, y, s, fontsize=fontsize, **kwargs)
        if not s:
            return txt
        max_px = data_width_to_px(max_width)
        bbox = txt.get_window_extent(renderer=renderer)
        while bbox.width > max_px and fontsize > 3:
            fontsize -= 0.5
            txt.set_fontsize(fontsize)
            bbox = txt.get_window_extent(renderer=renderer)
        return txt

    # Draw nodes
    for node, (x, y) in node_positions.items():
        # Calculate box dimensions based on number of fields and array contents
        box_height = 0.8  # Fixed height for type + fields + values
        box_width = calculate_node_width(node)  # Use the dynamic width calculation
        
        # Draw main node box
        node_box = FancyBboxPatch((x-box_width/2, y-box_height/2), box_width, box_height, 
                                 boxstyle="round,pad=0.02", 
                                 facecolor='lightblue', 
                                 edgecolor='black', 
                                 linewidth=1)
        ax.add_patch(node_box)
        
        # Add node type at top
        fit_text(x, y + box_height/2 - 0.1, node.elem_type, box_width - 0.12, 10,
                 ha='center', va='center', fontweight='bold')
        
        field_widths = calculate_field_widths(node)
        field_start_x = x - box_width/2 + node_x_padding
        
        # Draw fields and values
        current_field_x = field_start_x
        for field_width, (field_name, field_value) in zip(field_widths, node.dict.items()):
            field_x = current_field_x + field_width/2
            current_field_x += field_width
            
            # Draw field name with compact spacing
            fit_text(field_x, y + 0.15, field_name, field_width - 0.06, 8,
                     ha='center', va='center', fontweight='bold')
            
            # Draw value box under field name
            if isinstance(field_value, Element):
                # Child node - draw pointer box
                value_box = FancyBboxPatch((field_x - 0.25, y - 0.3), 0.5, 0.3,
                                         boxstyle="round,pad=0.01",
                                         facecolor='lightyellow',
                                         edgecolor='black',
                                         linewidth=0.5)
                ax.add_patch(value_box)
                ax.text(field_x, y - 0.15, "→", ha='center', va='center', fontsize=12, fontweight='bold')
                
                # Draw connection to child node
                if field_value in node_positions:
                    child_x, child_y = node_positions[field_value]
                    connection = ConnectionPatch((field_x, y - 0.3), (child_x, child_y + 0.4), 
                                             "data", "data", 
                                             arrowstyle="->", shrinkA=3, shrinkB=5,
                                             mutation_scale=15, fc="black")
                    ax.add_patch(connection)
                
            elif isinstance(field_value, list):
                # Lists get a bracketed strip with indexed cells and useful labels.
                list_width = calculate_list_width(field_value)
                list_x = field_x - list_width/2
                list_y = y - 0.32
                list_box = FancyBboxPatch((list_x, list_y), list_width, 0.34,
                                         boxstyle="round,pad=0.015",
                                         facecolor='#eef6ff',
                                         edgecolor='#6f8fb7',
                                         linewidth=0.75)
                ax.add_patch(list_box)
                ax.text(list_x + 0.07, y - 0.15, "[", ha='center', va='center',
                       fontsize=9, fontweight='bold', color='#4a5d75')
                ax.text(list_x + list_width - 0.07, y - 0.15, "]", ha='center',
                       va='center', fontsize=9, fontweight='bold', color='#4a5d75')

                if len(field_value) == 0:
                    fit_text(field_x, y - 0.15, "empty", list_width - 0.3, 6.5,
                             ha='center', va='center', color='#65758a', style='italic')

                item_x = list_x + list_bracket_pad
                for j, (child, child_label, cell_width) in enumerate(list_item_specs(field_value)):
                    cell_y = list_y + 0.05
                    cell_face = '#fff6d8' if isinstance(child, Element) else '#f8fafc'
                    cell_edge = '#d6a849' if isinstance(child, Element) else '#b7c0cc'
                    array_box = FancyBboxPatch((item_x, cell_y), cell_width, list_cell_height,
                                             boxstyle="round,pad=0.012",
                                             facecolor=cell_face,
                                             edgecolor=cell_edge,
                                             linewidth=0.65)
                    ax.add_patch(array_box)
                    ax.text(item_x + 0.055, cell_y + list_cell_height - 0.045, str(j),
                           ha='center', va='center', fontsize=5.5, color='#6b7280')
                    fit_text(item_x + cell_width/2, cell_y + list_cell_height/2 - 0.02,
                             truncate_label(child_label, 10), cell_width - 0.12, 6.2,
                             ha='center', va='center',
                             fontweight='bold' if isinstance(child, Element) else 'normal',
                             color='#2f3b4a')

                    if isinstance(child, Element):
                        # Draw connection to child
                        if child in node_positions:
                            child_x, child_y = node_positions[child]
                            connection = ConnectionPatch((item_x + cell_width/2, list_y), 
                                                     (child_x, child_y + 0.4), 
                                                     "data", "data", 
                                                     arrowstyle="-|>", shrinkA=3, shrinkB=5,
                                                     mutation_scale=12, fc="#41658a",
                                                     ec="#41658a", linewidth=0.9)
                            ax.add_patch(connection)

                    item_x += cell_width + list_cell_gap
                
            else:
                # Primitive value - draw value box sized to the field column
                value_box_width = max(0.5, field_width - 0.12)
                value_box = FancyBboxPatch((field_x - value_box_width/2, y - 0.3),
                                         value_box_width, 0.3,
                                         boxstyle="round,pad=0.01",
                                         facecolor='lightyellow',
                                         edgecolor='black',
                                         linewidth=0.5)
                ax.add_patch(value_box)
                
                # Add value text, soft-truncating then shrinking to fit the box
                fit_text(field_x, y - 0.15, truncate_label(field_value, 16),
                         value_box_width - 0.08, 8, ha='center', va='center')
    
    plt.show()

# Add a call to interpreterv4's Interpreter.run method
def run_with_plotting(program_text):
    """
    Run the interpreter and plot the AST.
    
    Args:
        program_text: The program text to parse and run
    """
    from interpreterv4 import Interpreter
    from brewparse import parse_program
    
    # Parse the program to get AST
    ast = parse_program(program_text)
    
    # Plot the AST
    plot_ast(ast)
    
    # Run the interpreter
    interpreter = Interpreter()
    interpreter.run(program_text)
    
    return interpreter.get_output()

# Example usage
if __name__ == "__main__":
    # Example program
    example_program = """
    [func main []
        [print "hello world"]
    ]
    """
    
    output = run_with_plotting(example_program)
    print("Program output:", output)
