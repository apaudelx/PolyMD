library(readxl)
library(dplyr)
library(ggplot2)
library(grid)

# Load data
df <- read_excel("input.xlsx") # Give the input path here
colnames(df) <- tolower(colnames(df))

# a) Force Field Type
ff_df <- df %>%
  filter(!is.na(`force field type`), `force field type` != "") %>%
  mutate(
    ff_type = case_when(
      grepl("all", `force field type`, ignore.case = TRUE)    ~ "All Atom",
      grepl("coarse", `force field type`, ignore.case = TRUE) ~ "Coarse Grained",
      grepl("united", `force field type`, ignore.case = TRUE) ~ "United Atom"
    )
  ) %>%
  count(ff_type) %>%
  mutate(
    pct = n / sum(n) * 100,
    label = sprintf("%d (%.1f%%)", n, pct)
  )

p_a <- ggplot(ff_df, aes(ff_type, n, fill = ff_type)) +
  geom_col(width = 0.75) +
  geom_text(aes(label = label), vjust = -0.35, size = 3.6) +
  scale_fill_manual(values = c(
    "All Atom" = "#118AB2",
    "Coarse Grained" = "#EF476F",
    "United Atom" = "#06D6A0"
  )) +
  labs(title = "Force Field Type Distribution", y = "Number of Records") +
  scale_y_continuous(expand = expansion(mult = c(0, 0.12))) +
  theme_classic(base_size = 14) +
  theme(
    axis.text.x = element_text(angle = 35, hjust = 1),
    legend.position = "none",
    panel.border = element_rect(color = "black", fill = NA, size = 0.8),
    axis.line = element_blank()
  )

# b) Property availability
property_labels <- c(
  "density" = "Density",
  "glass_transition_temp" = "Glass Transition Temperature",
  "youngs_modulus" = "Young's Modulus",
  "radius_gyration" = "Radius of Gyration",
  "diffusion_coefficient" = "Diffusion Coefficient",
  "viscosity" = "Viscosity"
)

prop_df <- df %>%
  filter(!is.na(value), value != "NA") %>%
  count(properties) %>%
  filter(properties %in% names(property_labels)) %>%
  mutate(
    name = property_labels[properties],
    pct = n / sum(n) * 100,
    label = sprintf("%d (%.1f%%)", n, pct)
  )

p_b <- ggplot(prop_df, aes(name, n, fill = name)) +
  geom_col(width = 0.75) +
  geom_text(aes(label = label), vjust = -0.35, size = 3.6) +
  scale_fill_manual(values = c(
    "Density" = "#118AB2",
    "Glass Transition Temperature" = "#06D6A0",
    "Radius of Gyration" = "#EF476F",
    "Young's Modulus" = "#FFD166",
    "Diffusion Coefficient" = "#9467BD",
    "Viscosity" = "#17BECF"
  )) +
  labs(title = "Polymer Property Availability", y = "Number of Records") +
  scale_y_continuous(expand = expansion(mult = c(0, 0.12))) +
  theme_classic(base_size = 14) +
  theme(
    axis.text.x = element_text(angle = 35, hjust = 1),
    legend.position = "none",
    panel.border = element_rect(color = "black", fill = NA, size = 0.8),
    axis.line = element_blank()
  )

# c) Origin Type (Pie CHart)
origin_df <- df %>%
  filter(`polymer origin type` %in% c("synthetic","natural","semi_synthetic","blend")) %>%
  count(`polymer origin type`)

p_c <- ggplot(origin_df, aes("", n, fill = `polymer origin type`)) +
  geom_col(width = 1, color = "white") +
  coord_polar("y") +
  scale_fill_manual(values = c(
    "synthetic" = "#118AB2",
    "natural" = "#06D6A0",
    "semi_synthetic" = "#FFD166",
    "blend" = "#EF476F"
  )) +
  labs(title = "Polymer Origin Type") +
  theme_void(base_size = 14) +
  theme(legend.position = "bottom")

# d) Composition (Pie chart)
arch_df <- df %>%
  filter(`polymer architecture` %in% c("homopolymer","copolymer","other")) %>%
  count(`polymer architecture`)

p_d <- ggplot(arch_df, aes("", n, fill = `polymer architecture`)) +
  geom_col(width = 1, color = "white") +
  coord_polar("y") +
  scale_fill_manual(values = c(
    "homopolymer" = "#EF476F",
    "copolymer" = "#118AB2",
    "other" = "#06D6A0"
  )) +
  labs(title = "Polymer Composition") +
  theme_void(base_size = 14) +
  theme(legend.position = "bottom")

# Final Merge
png("final_figure.png", width = 3600, height = 3000, res = 300)

grid.newpage()
pushViewport(viewport(layout = grid.layout(2, 2)))

print(p_a, vp = viewport(layout.pos.row = 1, layout.pos.col = 1))
grid.text("(a)", x = unit(0.02,"npc"), y = unit(0.98,"npc"), gp = gpar(fontsize=16, fontface="bold"))

print(p_b, vp = viewport(layout.pos.row = 1, layout.pos.col = 2))
grid.text("(b)", x = unit(0.52,"npc"), y = unit(0.98,"npc"), gp = gpar(fontsize=16, fontface="bold"))

print(p_c, vp = viewport(layout.pos.row = 2, layout.pos.col = 1))
grid.text("(c)", x = unit(0.02,"npc"), y = unit(0.48,"npc"), gp = gpar(fontsize=16, fontface="bold"))

print(p_d, vp = viewport(layout.pos.row = 2, layout.pos.col = 2))
grid.text("(d)", x = unit(0.52,"npc"), y = unit(0.48,"npc"), gp = gpar(fontsize=16, fontface="bold"))

dev.off()
