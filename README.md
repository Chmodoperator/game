# Nova Terra: Text Wars

A browser-based MMO strategy game built with Django and WebSockets featuring pure ASCII-style graphics and terminal-like interface.

## 🚀 Game Features * 

- **Text-based 50x50 world map** with ASCII visualization
- **Real-time multiplayer** via WebSocket connections  
- **Empire building** with multiple building types
- **Research system** with 9 different technology trees
- **Military combat** with turn-based battle simulation
- **Diplomacy system** with alliances and messaging
- **Global rankings** and competitive gameplay
- **World events** that affect all players
- **Command-line interface** for advanced players
- **Multiple color themes** (Matrix Green, Cyber Blue, Retro Amber, War Red)

## 🛠️ Installation & Setup

### Prerequisites
- Python 3.8+
- Redis server (for WebSocket channels)

### Installation Steps

1. **Clone and navigate to the project**:
   ```bash
   cd /opt/game
   source nova_terra_env/bin/activate
   ```

2. **Install Redis** (for WebSocket support):
   ```bash
   # Ubuntu/Debian
   sudo apt-get install redis-server
   
   # Start Redis
   sudo systemctl start redis-server
   ```

3. **Initialize the game world**:
   ```bash
   python manage.py init_world
   ```

4. **Create a superuser** (optional, for admin access):
   ```bash
   python manage.py createsuperuser
   ```

## 🎮 Running the Game

### Development Server
```bash
source nova_terra_env/bin/activate
python manage.py runserver 0.0.0.0:8000
```

### Production with Daphne (WebSocket support)
```bash
source nova_terra_env/bin/activate
daphne -b 0.0.0.0 -p 8000 nova_terra.asgi:application
```

The game will be available at: `http://localhost:8000`

## 🎯 How to Play

### Getting Started
1. **Register** a new commander account
2. **Create your empire** with a unique name and color
3. **Explore the world map** to find territories to conquer
4. **Build structures** to generate resources
5. **Research technologies** to unlock new capabilities
6. **Train armies** to defend and expand your territory
7. **Form alliances** or declare war on other players

### Game Interface

#### Command Terminal
Type commands in the terminal interface:
- `help` - Show available commands
- `status` - Display empire status
- `map [x] [y]` - View world map centered on coordinates
- `build [type]` - Construct buildings
- `research [type]` - Start research projects
- `attack [x] [y]` - Attack enemy territories

#### Keyboard Shortcuts
- `D` - Dashboard
- `M` - World Map  
- `B` - Buildings
- `R` - Research
- `H` - Help
- `S` - Status

### Building Types
- **Command Center**: Main base building
- **Power Plant**: Generates energy
- **Mine**: Produces minerals
- **Farm**: Generates food
- **Research Lab**: Enables technology research
- **Barracks**: Trains military units
- **Defense System**: Protects territories
- **Spy Network**: Enables espionage
- **Factory**: Produces advanced units

### Research Trees
- **Energy Efficiency**: Boost energy production
- **Mining Technology**: Improve mineral extraction
- **Agriculture**: Enhance food production
- **Military Tactics**: Strengthen armies
- **Defense Systems**: Better territorial defense
- **Espionage**: Intelligence gathering
- **Space Travel**: Future expansion capabilities
- **Artificial Intelligence**: Advanced automation
- **Quantum Computing**: Ultimate technology

### Combat System
- **Turn-based battles** with calculated outcomes
- **Army experience** affects combat effectiveness
- **Terrain bonuses** provide defensive advantages
- **Research bonuses** improve military performance
- **Random factors** keep battles unpredictable

## 🌍 Game World

### Territory Types
- **Plains** (.) - Balanced terrain, good for food
- **Mountains** (^) - Rich in minerals and energy, high defense
- **Desert** (~) - Energy production bonus
- **Forest** (#) - Excellent for food production
- **Water** (≈) - Impassable, strategic barriers
- **Volcanic** (*) - High energy and minerals, dangerous

### World Events
Random events affect all players:
- **Natural Disasters**: Reduce resource production
- **Alien Invasions**: Military threats
- **Economic Crises**: Resource market fluctuations
- **Technological Breakthroughs**: Research bonuses
- **Resource Discoveries**: Bonus materials
- **Rebellions**: Internal empire challenges

## 🏆 Strategy Tips

1. **Start Small**: Focus on securing your starting area before expanding
2. **Balance Resources**: Don't neglect any resource type
3. **Research Early**: Technology advantages compound over time
4. **Scout Wisely**: Knowledge of enemy positions is crucial
5. **Form Alliances**: Cooperation can be more powerful than conquest
6. **Defend Key Points**: Protect resource-rich territories
7. **Time Your Attacks**: Strike when enemies are weak or distracted

## 📊 Admin Interface

Access the Django admin at `/admin/` to:
- Manage player empires
- View and edit territories
- Monitor battles and alliances
- Create world events
- View game statistics

## 🔧 Development

### Project Structure
```
nova_terra/
├── accounts/          # User authentication and profiles
├── game/             # Core game mechanics
├── chat/             # Communication system
├── templates/        # HTML templates
├── static/          # CSS, JavaScript, assets
└── manage.py        # Django management
```

### Key Technologies
- **Django 5.2**: Web framework
- **Django Channels**: WebSocket support
- **Redis**: Message broker for real-time features
- **SQLite**: Database (configurable)
- **Pure CSS/JS**: No external frameworks for authentic terminal feel

## 🐛 Troubleshooting

### Common Issues

**WebSocket Connection Failed**:
- Ensure Redis is running: `sudo systemctl status redis-server`
- Check if port 8000 is available
- Use Daphne instead of Django dev server for WebSockets

**Database Issues**:
- Delete `db.sqlite3` and run migrations again
- Reset world: `python manage.py init_world --reset`

**Performance Issues**:
- Enable Redis caching
- Use PostgreSQL for production
- Consider CDN for static files

## 📜 License

This project is open source and available under the MIT License.

## 🚀 Future Features

- **Space exploration** to other planets
- **AI empires** for single-player challenges  
- **Economic trading** between players
- **Seasonal competitions** and tournaments
- **Mobile-responsive** interface
- **Sound effects** and ambient audio
- **Achievement system** with rewards
- **Historical battle logs** and statistics

---

**Command the Galaxy. Forge Your Empire. Dominate Nova Terra.**

Welcome to the most addictive text-based strategy game in the universe! 🌌 