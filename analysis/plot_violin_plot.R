library(ggplot2)
library(dplyr)
library(scales)
library(showtext)
library(patchwork)

# Fonts
font_add_google("Lato", "lato")
showtext_auto(FALSE)

# Read data
df <- read.csv("input.csv", stringsAsFactors = FALSE)

# Clean Data
df_clean <- df %>%
  mutate(
    Property_Studied = Properties,
    numeric_value = suppressWarnings(as.numeric(Value))
  ) %>%
  filter(!is.na(numeric_value), !is.na(Property_Studied))

# Property Labels
property_labels <- c(
  density = "Density (g/cm³)",
  glass_transition_temp = "Glass Transition Temperature (K)",
  radius_gyration = "Radius of Gyration (nm)",
  youngs_modulus = "Young's Modulus (GPa)",
  diffusion_coefficient = "Diffusion Coefficient (m²/s)",
  viscosity = "Viscosity (Pa·s)"
)

df_clean <- df_clean %>%
  mutate(
    Property_Label = ifelse(
      Property_Studied %in% names(property_labels),
      property_labels[Property_Studied],
      Property_Studied
    )
  )

# Plot Order
desired_order <- c(
  "density",
  "glass_transition_temp",
  "radius_gyration",
  "youngs_modulus",
  "diffusion_coefficient",
  "viscosity"
)

properties_all <- unique(df_clean$Property_Studied)
properties <- c(
  intersect(desired_order, properties_all),
  setdiff(properties_all, desired_order)
)

# Color definition
okabe_ito <- c(
  blue = "#0072B2",
  red  = "#D55E00",
  navy = "#000080"
)

# Voilin plot function
create_violin_plot <- function(data_sub, use_log = FALSE, prop_name = "") {
  
  if (!is.data.frame(data_sub) || nrow(data_sub) < 3) return(NULL)
  
  # Central 70% range
  p15 <- quantile(data_sub$numeric_value, 0.25, na.rm = TRUE)
  p85 <- quantile(data_sub$numeric_value, 0.75, na.rm = TRUE)
  if (prop_name == "Glass Transition Temperature (K)") {
    label_text <- sprintf("[%.1f, %.1f]", p15, p85)
  } else if (use_log) {
    label_text <- sprintf("[%.2g, %.2g]", p15, p85)
  } else {
    label_text <- sprintf("[%.1f, %.1f]", p15, p85)
  }
  
  data_shaded <- data_sub %>%
    filter(numeric_value >= p15 & numeric_value <= p85)
  
  p <- ggplot(
    data = data_sub,
    aes(x = "", y = numeric_value)
  ) +
    geom_violin(
      fill = okabe_ito["blue"],
      alpha = 0.55,
      trim = FALSE,
      color = "black"
    ) +
    geom_violin(
      data = data_shaded,
      fill = okabe_ito["red"],
      alpha = 0.75,
      trim = FALSE
    ) +
    stat_summary(
      fun = median,
      geom = "crossbar",
      width = 0.5,
      size = 0.6
    ) +
    geom_jitter(
      width = 0.12,
      size = 1.2,
      alpha = 0.35,
      color = okabe_ito["navy"]
    ) +
    labs(x = "", y = prop_name) +
    theme_minimal(base_family = "lato", base_size = 16) +
    theme(
      panel.grid = element_blank(),
      axis.text.x = element_blank(),
      axis.ticks.x = element_blank(),
      axis.text.y = element_text(size = 16, face = "bold", color = "black"),
      axis.ticks.y = element_line(color = "black", size = 0.6),
      axis.title.y = element_text(size = 18, face = "bold"),
      panel.border = element_rect(color = "black", fill = NA, size = 1),
      plot.margin = margin(10, 20, 10, 10)
    ) +
    annotate(
      "label",
      x = Inf, y = Inf,
      label = label_text,
      hjust = 1.1, vjust = 1.15,
      size = 5.5,
      family = "lato",
      fontface = "bold",
      fill = alpha("white", 0.7),
      label.r = unit(0.2, "lines"),
      label.padding = unit(0.25, "lines"),
      color = "black"
    )
  
  # Axis formatting
  if (use_log) {
    p <- p +
      scale_y_log10(labels = scientific_format()) +
      labs(y = paste0(prop_name, "\n(log scale)"))
  } else {
    p <- p +
      scale_y_continuous(
        labels = label_number(accuracy = 0.1)
      )
  }
  
  p
}

# Log scales
log_scale_props <- c(
  "diffusion_coefficient",
  "viscosity",
  "youngs_modulus",
  "radius_gyration"
)

df_log <- df_clean %>%
  filter(Property_Studied %in% log_scale_props, numeric_value > 0)

df_linear <- df_clean %>%
  filter(!Property_Studied %in% log_scale_props)

# Create plots
plot_list <- list()

for (prop in properties) {
  use_log <- prop %in% log_scale_props
  data_sub <- (if (use_log) df_log else df_linear) %>%
    filter(Property_Studied == prop)
  
  if (nrow(data_sub) >= 3) {
    prop_label <- unique(data_sub$Property_Label)[1]
    plot_list[[prop]] <- create_violin_plot(data_sub, use_log, prop_label)
  }
}

# Arrange and plot
if (length(plot_list) > 0) {
  
  final_plot <- wrap_plots(plot_list, ncol = 3)
  
  ggsave(
    "violin_plots.png",
    final_plot,
    width = 15,
    height = 10,
    dpi = 600,
    bg = "white"
  )
  
  cat("\nSaved: violin_plots.png (600 DPI)\n")
  cat(sprintf("Created %d violin plots\n\n", length(plot_list)))
  
} else {
  cat("\n No plots generated — check data counts.\n")
}
