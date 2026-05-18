import subprocess
import tempfile
import re
import xml.etree.ElementTree as ET

def run_dot_plain(dot_source, engine='dot'):
    # return plain layout text
    p = subprocess.run([engine, '-Tplain'], input=dot_source.encode('utf8'), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode != 0:
        raise RuntimeError(f'Graphviz {engine} failed: {p.stderr.decode()}')
    return p.stdout.decode('utf8')

def run_dot_svg(dot_source, engine='dot'):
    p = subprocess.run([engine, '-Tsvg'], input=dot_source.encode('utf8'), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode != 0:
        raise RuntimeError(f'Graphviz {engine} failed: {p.stderr.decode()}')
    return p.stdout.decode('utf8')

def parse_plain(plain_text):
    nodes = {}
    edges = []
    graph = {}
    for line in plain_text.splitlines():
        parts = line.split()
        if not parts:
            continue
        if parts[0] == 'graph':
            graph['width'] = float(parts[1])
            graph['height'] = float(parts[2])
            graph['bb'] = (float(parts[1]), float(parts[2]))
        elif parts[0] == 'node':
            # node name x y w h label
            name = parts[1]
            x = float(parts[2])
            y = float(parts[3])
            w = float(parts[4])
            h = float(parts[5])
            label = ' '.join(parts[6:])
            nodes[name] = {'x':x,'y':y,'w':w,'h':h,'label':label}
        elif parts[0] == 'edge':
            edges.append(parts[1:])
    return {'graph':graph,'nodes':nodes,'edges':edges}

def insert_bboxes_into_svg(svg_text, layout):
    # parse svg to find width/height
    try:
        root = ET.fromstring(svg_text)
    except Exception:
        return svg_text
    svg_ns = {'svg':'http://www.w3.org/2000/svg'}
    vb = root.get('viewBox')
    if vb:
        _,_,w,h = [float(x) for x in vb.split()]
    else:
        w = float(root.get('width') or 800)
        h = float(root.get('height') or 600)
    # Graphviz plain coords use points where 1 unit = inch? We'll assume px scaling by comparing graph bbox
    graph_w = layout['graph'].get('width', w)
    graph_h = layout['graph'].get('height', h)
    sx = w / graph_w
    sy = h / graph_h
    # build rect elements as string and inject before </svg>
    rects = []
    for name, n in layout['nodes'].items():
        # plain coords origin bottom-left; svg origin top-left
        x = n['x'] * sx
        y = h - (n['y'] * sy)
        rw = n['w'] * sx
        rh = n['h'] * sy
        rx = x - rw/2
        ry = y - rh/2
        rects.append(f'<rect x="{rx:.2f}" y="{ry:.2f}" width="{rw:.2f}" height="{rh:.2f}" fill="none" stroke="red" stroke-width="1"/>')
    insert_at = svg_text.rfind('</svg>')
    if insert_at == -1:
        return svg_text
    new_svg = svg_text[:insert_at] + '\n' + '\n'.join(rects) + svg_text[insert_at:]
    return new_svg

def layout_and_render(dot_source, engine='dot', annotate_bboxes=True):
    plain = run_dot_plain(dot_source, engine=engine)
    svg = run_dot_svg(dot_source, engine=engine)
    layout = parse_plain(plain)
    if annotate_bboxes:
        try:
            svg = insert_bboxes_into_svg(svg, layout)
        except Exception:
            pass
    return svg, plain
