import pygame
import numpy as np
import pandas as pd
import sys
import csv

# Initialize Pygame
pygame.init()

# Create screen
width, height = 1200, 800
screen = pygame.display.set_mode((width, height))
pygame.display.set_caption("Drag and Drop Names")

# set font size
fsize = 12
# set boundary between regions of the gui
x_bound = 600

# ----------------------------------------------------------- #
# load data
importSpreadsheet = True
week = 10
wname = 'main'
ffolder = 'lineup_builder/'
fname = f'dk_{wname}_week{week}.csv'

# Preprocess function to remove 'Jr.' or 'Jr' from names
def preprocess(name):
    return name.lower().replace("jr.", "").replace("jr", "").strip()
# Preprocess function to remove '.'
def preprocess2(name):
    return name.lower().replace(".", "").strip()

# location of the word 'Position' in the DK spreadsheet
# L23 -> skiprows = 22, usecols = 11: 25
# H25 -> skiprows = 24, usecols = 7: 21

data = pd.read_csv(ffolder + fname, skiprows = 24, usecols = range(7, 21), header = 0)
data.reset_index(drop=True, inplace=True)
# defense categories: S, CB, LB, DT, DE
data['Position'].replace(['S', 'CB', 'LB', 'DT', 'DE'], 'DEF', inplace=True)
# create a new column to use to match to the projection data
data['Match'] = np.where(data['Position'] == 'DEF', data['TeamAbbrev'] + ' DST', data['Name'])
data['Match'] = data['Match'].apply(preprocess)
data['Match'] = data['Match'].apply(preprocess2)
# create a new column with the game time
data['Game Time'] = data['Game Info'].apply(lambda x: x.split(' ')[4])

# fproj = f'etr_full_week{week}.csv'
fproj = 'Weekly Fantasy Projections.csv'
proj = pd.read_csv(ffolder + fproj)
proj['Match'] = proj['Player'].apply(preprocess)
proj['Match'] = proj['Player'].apply(preprocess2)
proj['Match'].replace(['la dst'], 'lar dst', inplace=True)
proj['Match'].replace(['josh palmer'], 'joshua palmer', inplace=True)
proj['Match'].replace(['kenneth walker'], 'kenneth walker iii', inplace=True)
proj['Match'].replace(['allen robinson'], 'allen robinson ii', inplace=True)
proj['Match'].replace(['calvin austin'], 'calvin austin iii', inplace=True)
proj['Match'].replace(['gardner minshew'], 'gardner minshew ii', inplace=True)


df_merge = pd.merge(data, proj, left_on = 'Match', right_on = 'Match', how = 'left')
# df_merge = pd.merge(data, proj, left_on = 'Match', right_on = 'Match', how = 'outer')
# df_merge.to_csv(ffolder + f'merge_week{week}.csv', index = False)

df_merge = df_merge[['Name', 'Position_x', 'TeamAbbrev', 'Card Rarity', 'DK', 'Card Set', 'Card Edition', 'Unique ID', 'Game Time']]
df_merge.columns = ['Name', 'Pos', 'Team', 'Rarity', 'Proj', 'Set', '#', 'ID', 'Time']

sort_order = {'Reignmaker': 4, 'Legendary': 3, 'Elite': 2, 'Rare': 1, 'Core': 0}
sort_order2 = {'QB': 8, 'RB': 7, 'WR': 6, 'TE': 5, 'K': 4, 'DEF': 3}
df_merge['Sort_Column'] = df_merge['Rarity'].map(sort_order)
df_merge['Sort_Column2'] = df_merge['Pos'].map(sort_order2)
df = df_merge.sort_values(by=['Sort_Column', 'Sort_Column2', 'Proj', '#'], ascending = False)
df.drop('Sort_Column', axis=1, inplace=True)
df.drop('Sort_Column2', axis=1, inplace=True)

# df.to_csv(ffolder + f'dk_etr_proj_week{week}.csv', index = False)

color_map = {
    'Reignmaker': (255, 215, 0),  # Gold
    'Legendary': (255, 255, 0),  # Yellow
    'Elite': (173, 216, 230),  # Blue
    'Rare': (0, 255, 0),  # Green
    'Core': (192, 192, 192)  # Grey
}

# Create initial data
categories = ['QB', 'RB', 'WR', 'WR/TE', 'FLEX']
Ngroups = 40
groups = []
for j in range(Ngroups):
    groups.append('Group {0}'.format(j))
cells = {}
buttons = []
dragging = None

# Scrolling variables
scroll_offset = 0
# max_scroll = len(df['Name']) * 40 - 400

# Initialize buttons based on DataFrame categories
buttons = []
col_offsets = {'QB': 0, 'RB': 100, 'WR': 200, 'TE': 300, 'K': 400, 'DEF': 500}
row_counters = {'QB': 0, 'RB': 0, 'WR': 0, 'TE': 0, 'K': 0, 'DEF': 0}  # separate row counter for each category

for i, (n, p, r, x, u, t, m) in enumerate(zip(df['Name'], df['Pos'], df['Rarity'], df['Proj'], df['ID'], df['Time'], df['Team'])):
    color = color_map.get(r, (255, 255, 255)) # default to white if no rarity
    x_offset = col_offsets[p]
    row = row_counters[p]  # get the current row counter for this category
    buttons.append((pygame.Rect(x_offset, row * 40, 90, 30), (n, x, u, t, m), color))
    row_counters[p] += 1  # increment the row counter for this category

max_scroll = len(buttons) * 40 - 400 


# Create cells for each group and category
x, y = 600, 20
cell_width, cell_height = 100, 16
for group in groups:
    cells[group] = {}
    x = 600
    for category in categories:
        cell = pygame.Rect(x, y, cell_width, cell_height)
        cells[group][category] = {'rect': cell, 'names': [], 'projs': [], 'ids': [], 'times': [], 'teams': [], 'color': (100, 100, 100)}
        x += cell_width + 20
    y += cell_height + 3

# Variables to differentiate between dragging from a cell or from the left column
dragging_from_cell = False
dragging_from_column = False

original_position = None  # sets variable for the original position of a button

# ----------------------------------------------------------- #
# import previously organized data

if importSpreadsheet:
    f_import = ffolder + f'dk_{wname}_week{week}_lineups.csv'
    df_imp = pd.read_csv(f_import)

    Nrows = len(df_imp['QB_id'])

    for nr in range(Nrows):

        positions = ['QB', 'RB', 'WR', 'WR/TE', 'FLEX']

        for pos in positions:

            posID = df_imp[f'{pos}_id'][nr]

            for button_data in buttons:
                button, (n, x, u, t, m), color = button_data
                if u == posID:
                    # print(n)
                    toCell = cells[f'Group {nr}'][pos]
                    toCell['names'].append(n)
                    toCell['projs'].append(x)
                    toCell['ids'].append(u)
                    toCell['times'].append(t)
                    toCell['teams'].append(m)
                    toCell['color'] = color

                    buttons.remove(button_data)

# ----------------------------------------------------------- #
# Main loop
clock = pygame.time.Clock()
while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit(0)

        # MOUSEBUTTONDOWN
        elif event.type == pygame.MOUSEBUTTONDOWN:
            pos = pygame.mouse.get_pos()
            # Scroll wheel down
            if event.button == 5:
                scroll_offset = min(max_scroll, scroll_offset + 40)
            # Scroll wheel up
            elif event.button == 4:
                scroll_offset = max(0, scroll_offset - 40)
            # Drag
            else:
                for button, (name, proj, uid, time, team), color in buttons:
                    scrolled_button = button.move(0, -scroll_offset)
                    if scrolled_button.collidepoint(pos):
                        # original_position = button.topleft  # original position before scrolling
                        dragging = (pygame.Rect(scrolled_button), name, proj, uid, time, team, color)
                        dragging_from_column = True
                        break # stop checking further buttons

                # If not dragging from the left column, check if dragging from cells
                if not dragging_from_column:
                    for group, categories in cells.items():
                        for category, cell_data in categories.items():
                            cell, names, projs, ids, times, teams, color = cell_data['rect'], cell_data['names'], cell_data['projs'], cell_data['ids'], cell_data['times'], cell_data['teams'], cell_data['color']
                            if cell.collidepoint(pos) and names:  # If the cell contains names
                                # original_cell_position = cell.topleft # original cell position
                                dragging = (pygame.Rect(cell), names[-1], projs[-1], ids[-1], times[-1], teams[-1], color)  # Pick up the last values from this cell
                                names.pop()  # Remove the last name from this cell
                                projs.pop()
                                ids.pop()
                                times.pop()
                                teams.pop()
                                cell_data['color'] = (100, 100, 100)  # Reset the color to original (adjust as needed)
                                dragging_from_cell = True
                                break  # Stop checking further cells

                        if dragging_from_cell:
                            break

        # MOUSEBUTTONUP
        elif event.type == pygame.MOUSEBUTTONUP:
            pos = pygame.mouse.get_pos()
            if dragging:
                if dragging_from_column:
                    for group, categories in cells.items():
                        for category, cell_data in categories.items():
                            cell, names, projs, ids, times, teams, color = cell_data['rect'], cell_data['names'], cell_data['projs'], cell_data['ids'], cell_data['times'], cell_data['teams'], cell_data['color']
                            if cell.collidepoint(pos):
                                names.append(dragging[1])
                                projs.append(dragging[2])
                                ids.append(dragging[3])
                                times.append(dragging[4])
                                teams.append(dragging[5])
                                cell_data['color'] = dragging[6]  # Set the color to match the button
                                buttons = [btn for btn in buttons if btn[1][2] != dragging[3]]  # Remove from the list
                                dragging_from_column = False
                                break  # Stop checking further cells
                        if not dragging_from_column:
                            break

                elif dragging_from_cell:
                    for button, (name, proj, uid, time, team), color in buttons:
                        scrolled_button = button.move(0, -scroll_offset)
                        if scrolled_button.collidepoint(pos):  # If the name is dropped back on the left column
                            buttons.append((pygame.Rect(button), (dragging[1], dragging[2], dragging[3]), dragging[4], dragging[5], dragging[6]))  # Add it back to buttons
                            dragging_from_cell = False
                            break  # Stop checking further buttons
                        # if not scrolled_button.collidepoint(pos):
                        #     button.topleft = original_cell_position

                    for group, categories in cells.items():
                        for category, cell_data in categories.items():
                            cell, names, projs, ids, times, teams, color = cell_data['rect'], cell_data['names'], cell_data['projs'], cell_data['ids'], cell_data['times'], cell_data['teams'], cell_data['color']
                            if cell.collidepoint(pos):
                                names.append(dragging[1])
                                projs.append(dragging[2])
                                ids.append(dragging[3])
                                times.append(dragging[4])
                                teams.append(dragging[5])
                                cell_data['color'] = dragging[6]
                                dragging_from_cell = False
                                break
                            # if not cell.collidepoint(pos):
                            #     button.topleft = original_cell_position

                        if not dragging_from_cell:
                            break

                # Clear dragging
                dragging = None
                dragging_from_cell = False
                dragging_from_column = False

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_s:  # When 's' key is pressed save groups to csv

                # Initialize a dictionary with position labels as keys
                df_data = {'QB': [], 'RB': [], 'WR': [], 'WR/TE': [], 'FLEX': [], 'QB_id': [], 'RB_id': [], 'WR_id': [], 'WR/TE_id': [], 'FLEX_id': []}

                # Loop through each group in the cells dictionary
                for group, categories in cells.items():
                    # Initialize a temporary dictionary to hold this group's data
                    temp_group_data = {}
                    for position, cell_data in categories.items():
                        # Concatenate names into a single string separated by commas
                        temp_group_data[position] = ', '.join(cell_data['names'])
                        # Concatenate IDs into a single string separated by commas
                        temp_group_data[f"{position}_id"] = ', '.join(cell_data['ids'])
                    
                    # Populate the df_data dictionary with this group's data
                    for position in ['QB', 'RB', 'WR', 'WR/TE', 'FLEX']:
                        df_data[position].append(temp_group_data.get(position, ''))
                        df_data[f"{position}_id"].append(temp_group_data.get(f"{position}_id", ''))

                # Create a DataFrame
                df_export = pd.DataFrame(df_data)

                # Save the DataFrame to CSV
                df_export.to_csv(ffolder + f'dk_{wname}_week{week}_lineups.csv', index=False)

    # Draw everything
    screen.fill((255, 255, 255))

    # Draw buttons with scrolling offset
    for button, (name, proj, uid, time, team), color in buttons:
        scrolled_button = button.move(0, -scroll_offset)
        if 0 <= scrolled_button.top <= height:
            pygame.draw.rect(screen, color, scrolled_button)
            font = pygame.font.SysFont(None, fsize)
            label = font.render(str(proj) + ' ' + name, True, (0, 0, 0))
            label2 = font.render(team + ' ' + time, True, (0, 0, 0))
            screen.blit(label, (scrolled_button.x + 10, scrolled_button.y + 5))
            screen.blit(label2, (scrolled_button.x + 10, scrolled_button.y + 15))

    # Draw column headers
    x_header = 635
    font = pygame.font.SysFont(None, fsize)
    for category in categories:
        label = font.render(f"{category}", True, (0, 0, 0))
        screen.blit(label, (x_header + 10, 10))
        x_header += cell_width + 20

    # Draw cells without scrolling offset
    for group, categories in cells.items():
        for category, cell_data in categories.items():
            pygame.draw.rect(screen, cell_data['color'], cell_data['rect'], 2)
            if cell_data['names']:
                combined_info = f"{str(cell_data['projs'][-1])} {cell_data['names'][-1]}"
                label = font.render(combined_info, True, (0, 0, 0))
                screen.blit(label, (cell_data['rect'].x + 10, cell_data['rect'].y + 4))

    # Draw loop for Dragging
    if dragging:
        mouse_x, mouse_y = pygame.mouse.get_pos()
        dragging[0].topleft = (mouse_x - 50, mouse_y - 15)
        pygame.draw.rect(screen, dragging[6], dragging[0])  # Use dragging[6] for the color
        font = pygame.font.SysFont(None, fsize)
        label = font.render(dragging[1], True, (0, 0, 0))
        screen.blit(label, (dragging[0].x + 10, dragging[0].y + 5))


    pygame.display.flip()
    clock.tick(30)




