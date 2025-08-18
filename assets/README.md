# Bot Assets

This directory contains visual assets for your Discord bot.

## Bot Avatar/Logo

### Requirements
- **Format**: PNG, JPG, or GIF
- **Size**: 512x512px minimum (recommended: 1024x1024px)
- **File size**: Maximum 10MB
- **Style**: Should work well at small sizes (32x32px)

### Recommendations for Science Bot

For a science-themed Discord bot, consider these design elements:

#### **Scientific Symbols**
- 🧬 DNA helix
- ⚛️ Atom symbol
- 🔬 Microscope
- 🧪 Test tube
- 📊 Molecular structure
- 🌌 Galaxy/space theme

#### **Color Schemes**
- **Professional**: Deep blue + white + silver
- **Modern**: Teal + dark gray + accent color
- **Academic**: Navy + gold + white
- **Tech**: Electric blue + black + cyan

#### **Design Tips**
- Keep it simple - will be viewed at 32x32px in Discord
- High contrast for visibility
- Avoid fine details that disappear when scaled down
- Consider a circular design (Discord crops to circle)

### Using Your Logo

1. **Save your logo** as `bot_avatar_no_text.png` in this directory
2. **Update .env** with `DISCORD_AVATAR_PATH=assets/bot_avatar_no_text.png`
3. **Restart the bot** - it will automatically update on startup

### Alternative Methods

You can also set the avatar through:
- **Discord Developer Portal** (recommended for initial setup)
- **Programmatically** using the bot's avatar utilities

### Example Science Bot Concepts

```
🧬 SciBot - DNA helix in a circle
⚛️ AtomBot - Stylized atom with orbiting electrons  
🔬 LabBot - Modern microscope icon
📊 DataBot - Graph/chart with molecular overlay
🌌 CosmosBot - Galaxy with scientific constellation
```

### Free Resources

- **Icons**: Heroicons, Feather Icons, Science Icons
- **Colors**: Coolors.co, Adobe Color
- **Design**: Canva, Figma (free tiers)
- **Inspiration**: Dribbble, Icon8

Remember: Your bot's avatar is the first thing users see - make it memorable and relevant to your scientific expertise!
