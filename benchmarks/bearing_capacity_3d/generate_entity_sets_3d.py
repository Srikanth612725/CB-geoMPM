#!/usr/bin/env python3
"""
Generate entity sets (node sets) for 3D boundary conditions
"""

import json

# Domain parameters (must match generate_inputs_3d.py)
domain_length = 30.0
domain_width = 30.0
domain_height = 20.0
dx = dy = dz = 0.5

nx_nodes = int(domain_length / dx) + 1  # 61
ny_nodes = int(domain_width / dy) + 1   # 61
nz_nodes = int(domain_height / dz) + 1  # 41

print(f"Nodes: {nx_nodes} × {ny_nodes} × {nz_nodes} = {nx_nodes * ny_nodes * nz_nodes}")

# Node set 0: Bottom face (z=0) - Fixed
bottom_nodes = []
for j in range(ny_nodes):
    for i in range(nx_nodes):
        node_id = 0 * nx_nodes * ny_nodes + j * nx_nodes + i
        bottom_nodes.append(node_id)

print(f"Bottom nodes (z=0): {len(bottom_nodes)}")

# Node set 1: Left face (x=0) - Roller in x
left_nodes = []
for k in range(nz_nodes):
    for j in range(ny_nodes):
        node_id = k * nx_nodes * ny_nodes + j * nx_nodes + 0
        left_nodes.append(node_id)

print(f"Left nodes (x=0): {len(left_nodes)}")

# Node set 2: Right face (x=max) - Roller in x
right_nodes = []
for k in range(nz_nodes):
    for j in range(ny_nodes):
        node_id = k * nx_nodes * ny_nodes + j * nx_nodes + (nx_nodes - 1)
        right_nodes.append(node_id)

print(f"Right nodes (x=max): {len(right_nodes)}")

# Node set 3: Front face (y=0) - Roller in y
front_nodes = []
for k in range(nz_nodes):
    for i in range(nx_nodes):
        node_id = k * nx_nodes * ny_nodes + 0 * nx_nodes + i
        front_nodes.append(node_id)

print(f"Front nodes (y=0): {len(front_nodes)}")

# Node set 4: Back face (y=max) - Roller in y
back_nodes = []
for k in range(nz_nodes):
    for i in range(nx_nodes):
        node_id = k * nx_nodes * ny_nodes + (ny_nodes - 1) * nx_nodes + i
        back_nodes.append(node_id)

print(f"Back nodes (y=max): {len(back_nodes)}")

# Create entity sets JSON
entity_sets = {
    "node_sets": [
        {"id": 0, "set": bottom_nodes},
        {"id": 1, "set": left_nodes},
        {"id": 2, "set": right_nodes},
        {"id": 3, "set": front_nodes},
        {"id": 4, "set": back_nodes}
    ],
    "particle_sets": [
        {"id": 0, "set": []},
        {"id": 1, "set": []}
    ]
}

# Write to file
with open("entity_sets.json", 'w') as f:
    json.dump(entity_sets, f, indent=2)

print("\nWrote entity_sets.json")
print("  - Node set 0: Bottom (fixed in x,y,z)")
print("  - Node set 1: Left face (fixed in x)")
print("  - Node set 2: Right face (fixed in x)")
print("  - Node set 3: Front face (fixed in y)")
print("  - Node set 4: Back face (fixed in y)")
