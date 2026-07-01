## ＡＵＲＯＲＡ extra figure: per-round metric decomposition (pTM / pLDDT / chromo contributions to sort_score)
suppressPackageStartupMessages({library(ggplot2); library(dplyr); library(tidyr); library(patchwork)})
root <- '/work/BioFluor-GFP-2026'
out_dir <- file.path(root,'docs','figures')

d <- read.csv(file.path(root,'results','analysis_data','candidates.csv'),
              stringsAsFactors=FALSE)
# Convert each metric to the contribution it makes to sort_score
# sort_score = pTM*0.40 + pLDDT*0.30 + chromo*0.30
d <- d %>%
  mutate(pTM_contrib      = ptm    * 0.40,
         pLDDT_contrib     = plddt  * 0.30,
         chromo_contrib    = chromo * 0.30)
# Keep top1 per stage
top1 <- d %>% group_by(stage) %>% slice_max(score, n=1) %>% ungroup()
stage_levels <- c('Initial','Local R1','Local R2','Local R3')
top1$stage <- factor(top1$stage, levels=stage_levels)

# Long format for stacked bar
long <- top1 %>%
  select(stage, pTM_contrib, pLDDT_contrib, chromo_contrib) %>%
  pivot_longer(-stage, names_to='component', values_to='value') %>%
  mutate(component = recode(component,
                            pTM_contrib   = 'pTM  (0.40 wt)',
                            pLDDT_contrib  = 'pLDDT  (0.30 wt)',
                            chromo_contrib = 'chromo pLDDT  (0.30 wt)'))

p1 <- ggplot(long, aes(stage, value, fill=component)) +
  geom_col(width=0.55, color='white') +
  scale_fill_manual(values=c('#17322b','#1f5c4d','#d6a83a')) +
  geom_text(aes(label=sprintf('%.3f', value)),
            position=position_stack(vjust=0.5),
            color='white', size=3.5, fontface='bold') +
  geom_text(data=top1, aes(stage, score, label=sprintf('total %.4f', score)),
            vjust=-0.6, color='#17322b', size=3.6, fontface='bold',
            inherit.aes=FALSE) +
  scale_y_continuous(limits=c(0, 1.05)) +
  labs(title='Top-1 score decomposition by stage',
       subtitle='Each color band is one component of sort_score (stacked)',
       x=NULL, y='contribution', fill=NULL) +
  theme_minimal(base_size=12) +
  theme(plot.title=element_text(face='bold', size=15, color='#17322b'),
        plot.subtitle=element_text(color='#5b6b64', size=10),
        panel.grid.minor=element_blank(),
        legend.position='top',
        legend.key.size=unit(0.35,'cm'),
        legend.text=element_text(size=9))

ggsave(file.path(out_dir,'05_score_decomposition.png'),
       p1, width=9, height=5.4, dpi=220)
cat('done\n')