library(ggplot2)
library(tidyr)
library(dplyr)

# Create data frame
metrics_data <- data.frame(
  property_name = c(
    "Density (g/cm³)",
    "Diffusion Coefficient (m²/s)",
    "Glass Transition Temperature (K)",
    "Radius of Gyration (nm)",
    "Viscosity (Pa s)",
    "Young's Modulus (GPa)",
    "Force Field",
    "Polymer System"
  ),
  Precision = c(0.9726, 0.7674, 0.9586, 0.9231, 1.0000, 0.9464, 0.9925, 0.9985),
  Recall = c(0.9660, 0.7174, 0.8580, 0.9114, 0.9697, 0.9217, 1.0000, 1.0000),
  F1_Score = c(0.9693, 0.7416, 0.9055, 0.9172, 0.9846, 0.9339, 0.9962, 0.9993)
)

# Define order of properties
property_order <- c(
  "Polymer System",
  "Force Field",
  "Density (g/cm³)",
  "Glass Transition Temperature (K)",
  "Radius of Gyration (nm)",
  "Young's Modulus (GPa)",
  "Diffusion Coefficient (m²/s)",
  "Viscosity (Pa s)"
)


# Color palatte
pub_colors <- list(
  origin = c("#2A9D8F", "#E9C46A", "#F4A261", "#E76F51"),
  composition = c("#6A4C93", "#FF595E"),
  primary = "#2C3E50",
  secondary = "#34495E",
  accent = "#3498DB"
)


# Reshape data for ggplot
metrics_long <- metrics_data %>%
  mutate(property_name = factor(property_name, levels = property_order)) %>%
  pivot_longer(
    cols = c(Precision, Recall, F1_Score),
    names_to = "Metric",
    values_to = "Value"
  ) %>%
  mutate(Metric = factor(Metric, levels = c("Precision", "Recall", "F1_Score")))


# Define color
pipeline_colors <- c(
  "Precision" = "#4472C4",  # Blue
  "Recall"    = "#ED7D31",  # Orange
  "F1_Score"  = "#70AD47"   # Green
)

#Create the plot
p <- ggplot(metrics_long, aes(x = property_name, y = Value, fill = Metric)) +
  geom_bar(
    stat = "identity",
    position = position_dodge(width = 0.65),
    width = 0.65,
    color = "white",
    linewidth = 0.3
  ) +
  scale_fill_manual(
    values = pipeline_colors,
    labels = c("Precision", "Recall", "F1 Score")
  ) +
  labs(
    title = "Classification Performance Metrics by Property",
    x = "Property",
    y = "Score",
    fill = NULL
  ) +
  theme_minimal(base_size = 16, base_family = "Helvetica") +
  theme(
    plot.title = element_text(hjust = 0.5, size = 20, face = "plain", color = "#1F3A60"),
    axis.text.x = element_text(angle = 45, hjust = 1, size = 16, face = "plain"),
    axis.text.y = element_text(size = 16, face = "plain"),
    axis.title.x = element_text(size = 18, face = "plain", color = "#1F3A60"),
    axis.title.y = element_text(size = 18, face = "plain", color = "#1F3A60"),
    legend.position = "top",
    legend.text = element_text(size = 16, face = "plain", color = "#1F3A60"),
    
    # Remove grid lines
    panel.grid.major = element_blank(),
    panel.grid.minor = element_blank(),
    
    #Add ticks for both axes
    axis.line.x = element_blank(),  # keep off since panel.border draws the frame
    axis.ticks.x = element_line(color = pub_colors$secondary, linewidth = 0.8),
    axis.ticks.y = element_line(color = pub_colors$secondary, linewidth = 0.8),
    axis.ticks.length = unit(0.2, "cm"),
    
    panel.border = element_rect(color = "#1F3A60", fill = NA, linewidth = 0.6),
    plot.margin = margin(15, 15, 15, 15)
  ) +
  coord_cartesian(ylim = c(0, 1.0), clip = "off") +
  scale_y_continuous(
    breaks = seq(0, 1, 0.2),     
    expand = c(0, 0)
  )

# Save png
ggsave("f1_metric_plot.png", p, width = 9, height = 7, dpi = 300, bg = "white")
