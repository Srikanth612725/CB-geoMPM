#!/usr/bin/env python3
"""
Generate COARSE 3D mesh for quick testing
1m cell size instead of 0.5m = 1/8 the particles
"""

# ============================================================================
# Domain Parameters - COARSE for quick testing
# ============================================================================
domain_length = 30.0  
domain_width = 30.0   
domain_height = 20.0  

dx = dy = dz = 1.0  # COARSE: 1m cells (was 0.5m)

nx_cells = int(domain_length / dx)
ny_cells = int(domain_width / dy)
nz_cells = int(domain_height / dz)

particles_per_cell = 8

print("COARSE MESH for quick testing")
print("Domain: {:.1f}m × {:.1f}m × {:.1f}m".format(domain_length, domain_width, domain_height))
print("Grid: {} × {} × {} cells".format(nx_cells, ny_cells, nz_cells))
print("Cell size: {:.2f}m × {:.2f}m × {:.2f}m".format(dx, dy, dz))

# Foundation Parameters
foundation_length = 7.2
foundation_width = 8.0
foundation_thickness = 1.0  # Increased for coarse mesh

foundation_center_x = domain_length / 2.0
foundation_center_y = domain_width / 2.0

soil_height = 15.0
foundation_z_bottom = soil_height
foundation_z_top = soil_height + foundation_thickness

print("\nFoundation: {:.1f}m × {:.1f}m × {:.1f}m".format(
    foundation_length, foundation_width, foundation_thickness))

# Generate nodes
print("\nGenerating nodes...")
nodes = []
node_id = 0

nx_nodes = nx_cells + 1
ny_nodes = ny_cells + 1
nz_nodes = nz_cells + 1

for k in range(nz_nodes):
    for j in range(ny_nodes):
        for i in range(nx_nodes):
            x = i * dx
            y = j * dy
            z = k * dz
            nodes.append([node_id, x, y, z])
            node_id += 1

nnodes = len(nodes)
print("Generated {} nodes".format(nnodes))

# Generate cells
print("Generating cells...")
cells = []

for k in range(nz_cells):
    for j in range(ny_cells):
        for i in range(nx_cells):
            n0 = k * nx_nodes * ny_nodes + j * nx_nodes + i
            n1 = k * nx_nodes * ny_nodes + j * nx_nodes + (i + 1)
            n2 = k * nx_nodes * ny_nodes + (j + 1) * nx_nodes + (i + 1)
            n3 = k * nx_nodes * ny_nodes + (j + 1) * nx_nodes + i
            n4 = (k + 1) * nx_nodes * ny_nodes + j * nx_nodes + i
            n5 = (k + 1) * nx_nodes * ny_nodes + j * nx_nodes + (i + 1)
            n6 = (k + 1) * nx_nodes * ny_nodes + (j + 1) * nx_nodes + (i + 1)
            n7 = (k + 1) * nx_nodes * ny_nodes + (j + 1) * nx_nodes + i
            cells.append([n0, n1, n2, n3, n4, n5, n6, n7])

ncells = len(cells)
print("Generated {} cells".format(ncells))

# Write mesh
mesh_file = "mesh-3d-coarse.txt"
with open(mesh_file, 'w') as f:
    f.write("{} {}\n".format(nnodes, ncells))
    for node in nodes:
        f.write("{:.6f} {:.6f} {:.6f}\n".format(node[1], node[2], node[3]))
    for cell in cells:
        f.write("{} {} {} {} {} {} {} {}\n".format(*cell))

print("Wrote {}".format(mesh_file))

# Generate soil particles
print("\nGenerating soil particles...")
soil_particles = []
px_offset = dx / 4.0
py_offset = dy / 4.0
pz_offset = dz / 4.0

for k in range(nz_cells):
    for j in range(ny_cells):
        for i in range(nx_cells):
            cell_center_x = (i + 0.5) * dx
            cell_center_y = (j + 0.5) * dy
            cell_center_z = (k + 0.5) * dz
            
            if cell_center_z < soil_height:
                for pz_idx in range(2):
                    for py_idx in range(2):
                        for px_idx in range(2):
                            px = cell_center_x - px_offset + px_idx * 2 * px_offset
                            py = cell_center_y - py_offset + py_idx * 2 * py_offset
                            pz = cell_center_z - pz_offset + pz_idx * 2 * pz_offset
                            soil_particles.append([px, py, pz])

nsoil = len(soil_particles)
print("Generated {} soil particles".format(nsoil))

with open("particles-soil-coarse.txt", 'w') as f:
    f.write("{}\n".format(nsoil))
    for p in soil_particles:
        f.write("{:.6f} {:.6f} {:.6f}\n".format(p[0], p[1], p[2]))

# Generate foundation particles
print("Generating foundation particles...")
foundation_particles = []

foundation_xmin = foundation_center_x - foundation_length / 2.0
foundation_xmax = foundation_center_x + foundation_length / 2.0
foundation_ymin = foundation_center_y - foundation_width / 2.0
foundation_ymax = foundation_center_y + foundation_width / 2.0

for k in range(nz_cells):
    for j in range(ny_cells):
        for i in range(nx_cells):
            cell_center_x = (i + 0.5) * dx
            cell_center_y = (j + 0.5) * dy
            cell_center_z = (k + 0.5) * dz
            
            if (foundation_xmin <= cell_center_x <= foundation_xmax and
                foundation_ymin <= cell_center_y <= foundation_ymax and
                foundation_z_bottom <= cell_center_z <= foundation_z_top):
                
                for pz_idx in range(2):
                    for py_idx in range(2):
                        for px_idx in range(2):
                            px = cell_center_x - px_offset + px_idx * 2 * px_offset
                            py = cell_center_y - py_offset + py_idx * 2 * py_offset
                            pz = cell_center_z - pz_offset + pz_idx * 2 * pz_offset
                            foundation_particles.append([px, py, pz])

nfoundation = len(foundation_particles)
print("Generated {} foundation particles".format(nfoundation))

with open("particles-foundation-coarse.txt", 'w') as f:
    f.write("{}\n".format(nfoundation))
    for p in foundation_particles:
        f.write("{:.6f} {:.6f} {:.6f}\n".format(p[0], p[1], p[2]))

print("\n" + "="*60)
print("COARSE MESH SUMMARY")
print("="*60)
print("Mesh: {} nodes, {} cells".format(nnodes, ncells))
print("Particles: {} soil + {} foundation = {} total".format(
    nsoil, nfoundation, nsoil + nfoundation))
print("Foundation area: {:.1f} m²".format(foundation_length * foundation_width))
print("Expected Q ≈ 1776 kN (Target: 2522 kN from Liu et al.)")
print("="*60)
