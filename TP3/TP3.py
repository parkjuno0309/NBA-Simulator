from cmu_112_graphics import *
import math, time, requests, json, requests_cache, string, random, decimal
from PIL import ImageTk, Image
from io import BytesIO


requests_cache.install_cache('nba_cache')
#code from https://pypi.org/project/requests-cache/
session = requests_cache.CachedSession('demo_cache')

API_KEY = "2d19586287f84fbcadd1e39a045a6349"
import json

#function that creates list of all team names
def getTeams():
    teams = []    
    for id in range(1,31):
        response = session.get("https://www.balldontlie.io/api/v1/teams/" + str(id))
        responseString = response.text
        responseDict = json.loads(responseString)
        teams.append(responseDict['full_name'])
    return teams

#function that creates list of team acronyms
def getTeamAcronyms():
    teamAcronyms = []
    response = session.get('https://www.balldontlie.io/api/v1/teams')
    responseJSON = response.json()
    for team in responseJSON['data']:
        teamAcronyms.append(team['abbreviation'])
    sortedAcronyms = sorted(teamAcronyms)
    sortedAcronyms[1], sortedAcronyms[2] = sortedAcronyms[2], sortedAcronyms[1]
    return sortedAcronyms


def filterName(nameString):
    # Split the name string into first and last name
    splitName = nameString.split()
    if len(splitName) == 2:
        firstName, lastName = splitName
    else:
        # Handle cases where the player has a middle name or initial
        firstName = splitName[0]
        lastName = ' '.join(splitName[1:])
    return firstName, lastName

###MODEL
def appStarted(app):
    resetApp(app)
    # ui parameters
    app.margin = app.width//10
    
    #ui parameters for team select screen
    app.rows = 5
    app.cols = 6
    app.playersPerTeam  = 12

    #ui parameters for court
    app.courtR = app.width//12
    app.playerR = app.width//50
    app.basketballR = app.width//70

def resetApp(app):
    # app states (screens)
    app.homeScreen = True
    app.helpScreen = False
    app.tendenciesScreen = False
    app.gameScreen = False
    app.started = False
    app.teamSelect = False
    app.rosterScreen = False
    app.paused = False
    app.substitutionScreen = False
    app.gameOverScreen = False
    app.playerStatsScreen = False
    app.opponentStatsScreen = False

    #app parameters
    app.message = ''
    app.selectedMode = -1
    app.startTime = 0
    app.time = 0
    app.posessionSwitchTime = 0
    app.teams = getTeams()
    app.teamAcronyms = getTeamAcronyms()
    app.teamRoster = getTeamPlayers('ATL')

    #team mode app selects
    app.selected = (0,0)
    app.selectedTeam = 'Atlanta Hawks'
    app.selectedTeamAcronym = 'ATL'
    app.selectedPlayer = 0
    app.selectedPlayerName = app.teamRoster[app.selectedPlayer]
    app.playerToSub = -1
    app.playing5 = getBestFive(app, app.teamRoster, 'ATL')[0]
    app.playing5Overalls = getBestFive(app, app.teamRoster, 'ATL')[1]
    app.playerCoordinates = [[app.width*(0.47), app.height//2],[app.width*(0.38), app.height//2], [app.width*(0.28), app.height//2],
        [app.width*(0.45), app.height*(0.33)], [app.width*(0.45), app.height*(0.67)]]
    app.playerStaminas = []
    app.playerPercentages = dict()
    app.playerFieldGoals = [0,0]

    #team mode opposing team info
    app.opposingTeam = 1
    app.opposingTeamAcronym = ''
    app.opposingTeamPlayers = []
    app.opposingTeamName = app.teams[app.opposingTeam]
    app.opposing5 = []
    app.opposing5Overalls = []
    app.opposingCoordinates = [[app.width*(0.53), app.height//2], [app.width*(0.62), app.height//2], [app.width*(0.77), app.height//2],
        [app.width*(0.55), app.height*(0.33)], [app.width*(0.55), app.height*(0.67)]]
    app.opponentStaminas = []
    app.opponentPercentages = dict()
    app.opponentFieldGoals = [0,0]

    #game paramters
    app.playerScore = 0
    app.opponentScore = 0
    app.quarter = 1
    app.basketballCoordinates = [app.width//2, app.height//2]
    app.possession = 0 #0 -> user possession, #1 -> CPU possession
    app.playerWithBall = 0
    app.playerWithBallName = ''
    app.playerWithBallPercentages = []
    app.userStats = {}
    app.opponentStats = {}
    app.speed = 1
    app.previousPlayerWithBall = 0

    #Tendencies parameters
    app.shotTendency = 0.5
    app.passTendency = 0.5
    app.threePointTendency = 0.5
    app.shotTendencyX = app.width*(0.6)
    app.passTendencyX = app.width*(0.6)
    app.threePointTendencyX = app.width*(0.6)

#returns list of players on a specific team
def getTeamPlayers(team):
    headers = {
        "Ocp-Apim-Subscription-Key": API_KEY
    }
    response = session.get(f"https://api.sportsdata.io/v3/nba/scores/json/Players?key={API_KEY}", headers=headers)
    responseJSON = response.json()
    players = [player['FirstName'] + ' ' + player['LastName'] for player in responseJSON if player['Team'] == team]
    return players[:12]

def getPlayerStats(player, team):
    name = player.lower()
    headers = {
        "Ocp-Apim-Subscription-Key": API_KEY
    }
    response = session.get(f"https://api.sportsdata.io/v3/nba/stats/json/PlayerSeasonStatsByTeam/2023/{team}?key={API_KEY}", headers=headers)
    responseJSON = response.json()
    playerData = next((player for player in responseJSON if player['Name'].lower() == name), None)
    if playerData:
        return playerData
    else:
        print(f"No stats found for player {player}")
        return None

def getPlayerRatings(player, team):
    individualRatings = []
    overallRating = 0
    statsDict = getPlayerStats(player, team)
    if statsDict:
        if statsDict['Games'] == 0:
            return [60, 60, 60, 60, 60, 60], 60 # default
        points_per_game = ((statsDict['TwoPointersMade'] * 2) + (statsDict['ThreePointersMade'] * 3) + (statsDict['FreeThrowsMade']))/statsDict['Games']
        individualRatings += [60 + int(points_per_game)] #scoring Rating
        individualRatings += [59 + 2.8*(int(float(statsDict['Assists']/statsDict['Games'])))]  #passing Rating
        individualRatings += [50 + 10.5*(int(float(statsDict['ThreePointersMade']/statsDict['Games'])))] #threepoint Rating
        individualRatings += [49 + 2.6*(int(float(statsDict['Rebounds']/statsDict['Games'])))] #rebounding Rating
        individualRatings += [50 + 17*(int(float(statsDict['Steals']/statsDict['Games'])))]  #steal Rating
        individualRatings += [50 + 8*(int(float(statsDict['BlocksPercentage'])))] #block Rating
        for i in range(len(individualRatings)):
            if individualRatings[i] > 100:
                individualRatings[i] = 100
            overallRating += individualRatings[i]
        overallRating //= 5.1
        if overallRating >= 100:
            return individualRatings, 99
        else:
            return individualRatings, overallRating
    else:
        return [], 0

def getPlayerPercentages(app, player, team):
    percentages = []
    playerRatings = getPlayerRatings(player, team)[0]
    percentages += [(playerRatings[0]/1.6)/100] #scoring percentage
    percentages += [(playerRatings[1]*1.22)/100] #pass completion percentage
    percentages += [(playerRatings[2]/2.2)/100] #three point percentage
    percentages += [(playerRatings[3])/100] #rebounds percentage
    percentages += [(playerRatings[4]/4)/100] #steal percentage
    percentages += [(playerRatings[5]/7)/100] #block percentage
    for i in range(len(percentages)):
        if percentages[i] > 1:
            percentages[i] = 0.98
    return percentages

def getBestFive(app, teamRoster, team): #####
    bestFive = []
    bestFiveOveralls = []
    for i in range(len(teamRoster)):
        player = teamRoster[i]
        overallRating = int(getPlayerRatings(player, team)[1])
        if len(bestFive) < 5:
            bestFive.append(player)
            bestFiveOveralls.append(overallRating)
        else:
            if overallRating >= min(bestFiveOveralls):
                index = bestFiveOveralls.index(min(bestFiveOveralls))
                bestFive.pop(index)
                bestFive.insert(index, player)
                bestFiveOveralls.pop(index)
                bestFiveOveralls.insert(index, overallRating)
    return bestFive, bestFiveOveralls

def createStatsDict(app, L):
    d = dict()
    for i in range(len(L)):
        d[L[i]] = [0,0,0,0,0] #points, rebounds, assists, steals, blocks
    return d

def createStaminaDict(app, L):
    staminas = dict()
    for i in range(len(L)):
        staminas[L[i]] = 100
    return staminas

def createPlayerPercentagesDict(app, L):
    for i in range(len(L)):
        app.playerPercentages[L[i]] = getPlayerPercentages(app, L[i], app.selectedTeamAcronym)

def createOpponentPlayerPercentagesDict(app, L):
    for i in range(len(L)):
        app.opponentPercentages[L[i]] = getPlayerPercentages(app, L[i], app.opposingTeamAcronym)

#code copied from https://www.geeksforgeeks.org/python-program-for-selection-sort/
def selectionSort(A, B):
    newA = copy.deepcopy(A)
    newB = copy.deepcopy(B)
    for i in range(len(newA)):
        min_idx = i
        for j in range(i+1, len(newA)):
            if newA[min_idx] > newA[j]:
                min_idx = j  
        newA[i], newA[min_idx] = newA[min_idx], newA[i]
        newB[i], newB[min_idx] = newB[min_idx], newB[i]
    return [newA, newB]

def arrangePlayerOveralls(app, L1, L2):
    arrangedPlaying5 = selectionSort(app.playing5Overalls, L1)
    arrangedOpposing5 = selectionSort(app.opposing5Overalls, L2)
    return arrangedPlaying5, arrangedOpposing5

def arrangeReboundOveralls(app, L1):
    if L1 == app.opposing5:
        reboundRatings = []
        for i in range(len(L1)):
            playerRating = getPlayerPercentages(app, L1[i], app.opposingTeamAcronym)
            reboundRating = playerRating[3]
            reboundRatings.append(reboundRating)
        arrangedReboundRatings = selectionSort(reboundRatings, L1)
        return arrangedReboundRatings
    else:
        reboundRatings = []
        for i in range(len(L1)):
            playerRating = getPlayerPercentages(app, L1[i], app.selectedTeamAcronym)
            reboundRating = playerRating[3]
            reboundRatings.append(reboundRating)
        arrangedReboundRatings = selectionSort(reboundRatings, L1)
        return arrangedReboundRatings

def substituteOpposingPlayers(app, n): #sub opposing players based on their stamina
    j = random.randint(0,11)
    if (app.opponentStaminas[app.opposingTeamPlayers[j]] >= 70
        and app.opposingTeamPlayers[j] not in app.opposing5):
        app.opposing5[n] = app.opposingTeamPlayers[j]
        return
    else: 
        substituteOpposingPlayers(app, n)

###CONTROLLERS
def keyPressed(app, event):
    if event.key == 'r':
        resetApp(app)

def mousePressed(app, event):
    #home screen
    if app.homeScreen:
        if clickedHomeStartButton(app, event.x, event.y):
                app.teamSelect = not app.teamSelect
                app.homeScreen = not app.homeScreen
        if clickedHelpButton(app, event.x, event.y):
            app.homeScreen = not app.homeScreen
            app.helpScreen = not app.helpScreen
            
    #team select screen
    elif app.teamSelect:
        if clickedNextButton(app, event.x, event.y) and app.selected != None:
            app.teamSelect = not app.teamSelect
            app.rosterScreen = not app.rosterScreen
        elif clickedBackButton(app, event.x, event.y):
            app.teamSelect = not app.teamSelect
            app.homeScreen = not app.homeScreen
        else:
            if pointInGrid(app, event.x, event.y):
                app.selected = getCell(app, event.x, event.y)
                i = app.selected[0] + app.selected[1] + (5*app.selected[0])
                app.selectedTeam = app.teams[i]
                app.teamRoster = getTeamPlayers(app.teamAcronyms[i])
                app.selectedTeamAcronym = app.teamAcronyms[i]
                app.selectedPlayerName = app.teamRoster[app.selectedPlayer]
                app.playing5, app.playing5Overalls = getBestFive(app, app.teamRoster, app.selectedTeamAcronym)

    #roster screen
    elif app.rosterScreen:
        if clickedBackButton(app, event.x, event.y):
            app.rosterScreen = not app.rosterScreen
            app.teamSelect = not app.teamSelect 
            app.playing5 = []
            app.selectedPlayer = 0
        elif clickedNextButton(app, event.x, event.y) and len(app.playing5) == 5:
            app.rosterScreen = not app.rosterScreen
            app.gameScreen = not app.gameScreen
            app.opposingTeam = random.randint(0,29)
            if app.teams[app.opposingTeam] == app.selectedTeam:
                app.opposingTeam += 1
            app.opposingTeamAcronym = app.teamAcronyms[app.opposingTeam]
            app.opposingTeamPlayers = getTeamPlayers(app.opposingTeamAcronym)
            app.opposing5, app.opposing5Overalls = getBestFive(app, app.opposingTeamPlayers, app.opposingTeamAcronym)
            app.userStats = createStatsDict(app, app.playing5)
            app.opponentStats = createStatsDict(app, app.opposing5)
            app.opposingTeamName = app.teams[app.opposingTeam]
            app.opponentStaminas = createStaminaDict(app, app.opposingTeamPlayers)
            app.playerStaminas = createStaminaDict(app, app.teamRoster)
            createPlayerPercentagesDict(app, app.teamRoster)
            createOpponentPlayerPercentagesDict(app, app.opposingTeamPlayers)
        elif (clickedSelectButton(app, event.x, event.y) and 
            app.selectedPlayerName not in app.playing5):
            overallRating = int(getPlayerRatings(app.selectedPlayerName, app.selectedTeamAcronym)[1])
            print(overallRating)
            if len(app.playing5) < 5:
                app.playing5 += [app.selectedPlayerName]
                app.playing5Overalls += [overallRating]
            else:
                if app.playerToSub != -1:
                    app.playing5.pop(app.playerToSub)
                    app.playing5.insert(app.playerToSub, app.selectedPlayerName)
                    app.playing5Overalls.pop(app.playerToSub)
                    app.playing5Overalls.insert(app.playerToSub, overallRating)
        elif pointInPlaying5Rect(app, event.x, event.y):
            app.playerToSub = getCol(app, event.x, event.y)
        else:
            if pointInRect(app, event.x, event.y):
                app.selectedPlayer = getRow(app, event.x,  event.y)
                app.selectedPlayerName = app.teamRoster[app.selectedPlayer]
            else:
                return

    #help screen
    elif app.helpScreen:
        if clickedBackButton(app, event.x, event.y):
            if app.oneOnOne == True:
                app.helpScreen = not app.helpScreen
                app.oneVOneScreen = not app.oneVOneScreen
            else:
                app.helpScreen = not app.helpScreen
                app.homeScreen = not app.homeScreen

    #tendencies screen
    elif app.tendenciesScreen:
        if clickedBackButton(app, event.x, event.y):
            app.tendenciesScreen = not app.tendenciesScreen
            app.gameScreen = not app.gameScreen
            app.paused = not app.paused
        if clickedShotTendencyBar(app, event.x, event.y):
            app.shotTendencyX = event.x
            app.shotTendency = (app.shotTendencyX - app.width*(0.4))/(app.width*(3/4) - app.width*(0.4))
        if clickedPassTendencyBar(app, event.x, event.y):
            app.passTendencyX = event.x
            app.passTendency = (app.passTendencyX - app.width*(0.4))/(app.width*(3/4) - app.width*(0.4))
        if clickedThreePointTendencyBar(app, event.x, event.y):
            app.threePointTendencyX = event.x
            app.threePointTendency = (app.threePointTendencyX - app.width*(0.4))/(app.width*(3/4) - app.width*(0.4))
    
    #game screen
    elif app.gameScreen:
        if clickedStartButton(app, event.x, event.y) and app.time == 0 and app.quarter <= 4:
            app.startTime = time.time()  
            app.started = not app.started
            if app.possession == 0:
                app.playerWithBallName = app.playing5[app.playerWithBall]
                app.playerWithBallPercentages = getPlayerPercentages(app, app.playerWithBallName, app.selectedTeamAcronym)
            elif app.possession == 1:
                app.playerWithBallName = app.opposing5[app.playerWithBall]
                app.playerWithBallPercentages = getPlayerPercentages(app, app.playerWithBallName, app.opposingTeamAcronym)
        elif clickedStartButton(app, event.x, event.y):
            app.paused = not app.paused
        if clickedSubButton(app, event.x, event.y):
            app.substitutionScreen = not app.substitutionScreen
            app.gameScreen = not app.gameScreen
            app.paused = True
        if clickedTendenciesButton(app, event.x, event.y):
            app.gameScreen = not app.gameScreen
            app.tendenciesScreen = not app.tendenciesScreen
            app.paused = True
        if clickedFastForwardButton(app, event.x, event.y):
            if app.speed == 8:
                app.speed = 1
            else:
                app.speed *= 2

    #substitution screen
    elif app.substitutionScreen:
        if clickedNextButton(app, event.x, event.y):
            app.substitutionScreen = not app.substitutionScreen
            app.gameScreen = not app.gameScreen
            app.paused = not app.paused
        elif (clickedSelectButton(app, event.x, event.y) and 
            app.selectedPlayerName not in app.playing5):
            overallRating = int(getPlayerRatings(app.selectedPlayerName, app.selectedTeamAcronym)[1])
            if len(app.playing5) < 5:
                app.playing5 += [app.selectedPlayerName]
                app.playing5Overalls += [overallRating]
            else:
                if app.playerToSub != -1:
                    app.playing5.pop(app.playerToSub)
                    app.playing5.insert(app.playerToSub, app.selectedPlayerName)
                    app.playing5Overalls.pop(app.playerToSub)
                    app.playing5Overalls.insert(app.playerToSub, overallRating)
        elif pointInPlaying5Rect(app, event.x, event.y):
            app.playerToSub = getCol(app, event.x, event.y)
        else:
            if pointInRect(app, event.x, event.y):
                app.selectedPlayer = getRow(app, event.x,  event.y)
                app.selectedPlayerName = app.teamRoster[app.selectedPlayer]
            else:
                return
    
    #gameOver screen
    elif app.gameOverScreen:
        if clickedPlayerStatsButton(app, event.x, event.y):
            app.playerStatsScreen = not app.playerStatsScreen
            app.gameOverScreen = not app.gameOverScreen
        elif clickedOpponentStatsButton(app, event.x, event.y):
            app.opponentStatsScreen = not app.opponentStatsScreen
            app.gameOverScreen = not app.gameOverScreen
    
    #playerStatsScreen
    elif app.playerStatsScreen:
        if pointInRect(app, event.x, event.y):
            app.selectedPlayer = getRow(app, event.x,  event.y)
            app.selectedPlayerName = app.teamRoster[app.selectedPlayer]
        elif clickedBackButton(app, event.x, event.y):
            app.playerStatsScreen = not app.playerStatsScreen
            app.gameOverScreen = not app.gameOverScreen
    
    elif app.opponentStatsScreen:
        if pointInRect(app, event.x, event.y):
            app.selectedPlayer = getRow(app, event.x,  event.y)
            app.selectedPlayerName = app.opposingTeamPlayers[app.selectedPlayer]
        elif clickedBackButton(app, event.x, event.y):
            app.opponentStatsScreen = not app.opponentStatsScreen
            app.gameOverScreen = not app.gameOverScreen

def timerFired(app):
    if not app.paused:
        if (app.started and app.quarter <= 4) or app.quarter >= 5:
            app.time = round(app.time + 0.1*app.speed, 1)
            if app.time%1 == 0.0:
                for player in app.teamRoster: #recover from stamina
                    if app.playerStaminas[player] < 100 and player not in app.playing5:
                        app.playerStaminas[player] += 3
                        app.playerStaminas[player] = int(app.playerStaminas[player])
                        if int(app.playerStaminas[player]) == 101 or int(app.playerStaminas[player]) == 102:
                            app.playerStaminas[player] = 100
                        for i in range(len(app.playerPercentages[app.playing5[0]])-2):
                            app.playerPercentages[player][i] += 0.005
                for opponent in app.opposingTeamPlayers:
                    if app.opponentStaminas[opponent] < 100 and opponent not in app.opposing5:
                        app.opponentStaminas[opponent] += 3
                        app.opponentStaminas[opponent] = int(app.opponentStaminas[opponent])
                        if int(app.opponentStaminas[opponent]) == 101:
                            app.opponentStaminas[opponent] = 100
                        for i in range(len(app.playerPercentages[app.playing5[0]])-2):
                            app.opponentPercentages[opponent][i] += 0.005
                for i in range(len(app.opposing5)):
                    if app.opponentStaminas[app.opposing5[i]] <= 45:
                        substituteOpposingPlayers(app, i)
            if 0 <= round(app.time%(1/app.passTendency),1) <= 0.1:
                passCompletionPercentage = app.playerWithBallPercentages[1] #check if pass is completed based on rating
                randomDecimal = float(random.randrange(0, 80)/100)
                if randomDecimal <= passCompletionPercentage: 
                    app.previousPlayerWithBall = app.playerWithBall
                    arrangedPlaying5, arrangedOpposing5 = arrangePlayerOveralls(app, app.playing5, app.opposing5)
                    randint = random.randrange(0,100)
                    if app.possession == 0:
                        if 0 <= randint <= 30: #makes sure best player gets more opportunities
                            highestOverallPlayer = arrangedPlaying5[1][4]
                            app.playerWithBall = app.playing5.index(highestOverallPlayer)
                        elif 31 <= randint <= 55:
                            secondOverallPlayer = arrangedPlaying5[1][3]
                            app.playerWithBall = app.playing5.index(secondOverallPlayer)
                        elif 56 <= randint <= 73:
                            thirdOverallPlayer = arrangedPlaying5[1][2]
                            app.playerWithBall = app.playing5.index(thirdOverallPlayer)
                        elif 74 <= randint <= 86:
                            fourthOverallPlayer = arrangedPlaying5[1][1]
                            app.playerWithBall = app.playing5.index(fourthOverallPlayer)
                        elif 87 <= randint <= 100:
                            fifthOverallPlayer = arrangedPlaying5[1][0]
                            app.playerWithBall = app.playing5.index(fifthOverallPlayer)
                    else:
                        if 0 <= randint <= 30: #makes sure best player gets more opportunities
                            highestOverallPlayer = arrangedOpposing5[1][4]
                            app.playerWithBall = app.opposing5.index(highestOverallPlayer)
                        elif 31 <= randint <= 55:
                            secondOverallPlayer = arrangedOpposing5[1][3]
                            app.playerWithBall = app.opposing5.index(secondOverallPlayer)
                        elif 56 <= randint <= 73:
                            thirdOverallPlayer = arrangedOpposing5[1][2]
                            app.playerWithBall = app.opposing5.index(thirdOverallPlayer)
                        elif 74 <= randint <= 86:
                            fourthOverallPlayer = arrangedOpposing5[1][1]
                            app.playerWithBall = app.opposing5.index(fourthOverallPlayer)
                        elif 87 <= randint <= 100:
                            fifthOverallPlayer = arrangedOpposing5[1][0]
                            app.playerWithBall = app.opposing5.index(fifthOverallPlayer)
                else:
                    app.possession = 1 - app.possession
                if app.possession == 0:
                    randomDecimal2 = float(decimal.Decimal(random.randrange(000, 100))/100)
                    opponentPlayerName = app.opposing5[app.playerWithBall]
                    opponentPercentages = getPlayerPercentages(app, opponentPlayerName, app.opposingTeamAcronym)
                    if randomDecimal2 <= opponentPercentages[4]:
                        app.possession = 1 - app.possession
                        if opponentPlayerName in app.opponentStats:
                            app.opponentStats[opponentPlayerName][3] += 1
                        elif opponentPlayerName in app.opposingTeamPlayers:
                            app.opponentStats[opponentPlayerName] = [0,0,0,1,0]
                else:
                    randomDecimal3 = float(decimal.Decimal(random.randrange(000, 100))/100)
                    userPlayerName = app.playing5[app.playerWithBall]
                    userPlayerPercentages = getPlayerPercentages(app, userPlayerName, app.selectedTeamAcronym)
                    if randomDecimal3 <= userPlayerPercentages[4]:
                        app.possession = 1 - app.possession
                        if userPlayerName in app.userStats:
                            app.userStats[userPlayerName][3] += 1
                        elif userPlayerName in app.teamRoster:
                            app.userStats[userPlayerName] = [0,0,0,1,0]
            if app.possession == 0:
                doStepPlayerMovements(app)
                if app.posessionSwitchTime > 3/app.speed:
                    doStepPlayerShot(app)
            else:
                doStepOpponentMovements(app)
                if app.posessionSwitchTime > 3/app.speed:
                    doStepOpponentShot(app)
        else:
            return
        if app.time >= 60:
            app.started = not app.started
            app.time = 0
            if app.quarter < 4 or app.playerScore == app.opponentScore:
                app.playerCoordinates = [[app.width*(0.47), app.height//2],[app.width*(0.38), app.height//2], [app.width*(0.28), app.height//2],
                    [app.width*(0.45), app.height*(0.33)], [app.width*(0.45), app.height*(0.67)]]
                app.opposingCoordinates = [[app.width*(0.53), app.height//2], [app.width*(0.62), app.height//2], [app.width*(0.77), app.height//2],
                    [app.width*(0.55), app.height*(0.33)], [app.width*(0.55), app.height*(0.67)]]
                app.basketballCoordinates = [app.width//2, app.height//2]
                app.quarter += 1
            else:
                if app.playerScore > app.opponentScore:
                    app.winner = app.selectedTeam
                else:
                    app.winner = app.teams[app.opposingTeam]
                app.gameOverScreen = not app.gameOverScreen
                app.gameScreen = not app.gameScreen
                return
    else:
        app.startTime = app.startTime
        app.time = app.time

#stamina -> changes speed and shot percentages
def doStepPlayerMovements(app): #when user possession
    app.posessionSwitchTime += 0.1

    #PLAYER 1 movements
    player1 = app.playerCoordinates[0]
    player1X = player1[0]
    player1Y = player1[1]
    opponent1 = app.opposingCoordinates[0]
    opponent1X = opponent1[0]
    opponent1Y = opponent1[1]
    distanceTraveled = 0
    if player1X <= app.width*(0.75):
        startPosition = player1X
        player1X += (app.width - app.margin - app.playerR - player1X)//(10/app.speed)*(app.playerStaminas[app.playing5[0]]/120)
        app.playerCoordinates[0][0] = player1X
        app.opposingCoordinates[0] = [player1X + 2.5*app.playerR, player1Y]
        distanceTraveled = (player1X - startPosition)
        app.playerStaminas[app.playing5[0]] = round(app.playerStaminas[app.playing5[0]] - distanceTraveled/240, 1)
        app.opponentStaminas[app.opposing5[0]] = round(app.opponentStaminas[app.opposing5[0]] - distanceTraveled/240, 1)
        for i in range(len(app.playerPercentages[app.playing5[0]])-2):
            if i == 0 or i ==2:
                app.playerPercentages[app.playing5[0]][i] -= 0.002
                app.opponentPercentages[app.opposing5[0]][i] -= 0.002
    elif (app.width*(0.78) <= player1X <= app.width*(0.85) or 
        app.height*(0.4) <= player1Y < app.height*(0.6)):
        player1X += random.randint(-3,3)
        player1Y += random.randint(-3,3)
        app.playerCoordinates[0] = [player1X, player1Y]
        app.opposingCoordinates[0] = [player1X + 2.5*app.playerR, player1Y]

    #PLAYER 2 movements
    player2 = app.playerCoordinates[1]
    player2X = player2[0]
    player2Y = player2[1]
    opponent2 = app.opposingCoordinates[1]
    opponent2X = opponent2[0]
    opponent2Y = opponent2[1]
    distanceTraveled = 0
    if player2X <= app.width*(0.65):
        startPosition = [player2X, player2Y]
        player2X += (app.width - app.margin - app.playerR - player2X)//(15/app.speed)*(app.playerStaminas[app.playing5[1]]/120)
        player2Y -= (player2Y - app.height*(0.2) - 2*app.playerR)//(10/app.speed)*(app.playerStaminas[app.playing5[1]]/120)
        app.playerCoordinates[1] = [player2X, player2Y]
        app.opposingCoordinates[1] = [player2X + 2.5*app.playerR, player2Y]
        distanceTraveled = math.sqrt((player2X - startPosition[0])**2 + (player2Y - startPosition[1])**2)
        app.playerStaminas[app.playing5[1]] = round(app.playerStaminas[app.playing5[1]] - distanceTraveled/240, 1)
        app.opponentStaminas[app.opposing5[1]] = round(app.opponentStaminas[app.opposing5[1]] - distanceTraveled/240, 1)
        for i in range(len(app.playerPercentages[app.playing5[1]])-2):
            if i == 0 or i ==2:
                app.playerPercentages[app.playing5[1]][i] -= 0.002
                app.opponentPercentages[app.opposing5[1]][i] -= 0.002
    elif (app.width*(0.65) <= player2X <= app.width*(0.8) - app.playerR or 
        app.margin + app.playerR <= player2Y <= app.height*(0.5)): 
        player2X += random.randint(-3,3)
        player2Y += random.randint(-3,2)
        app.playerCoordinates[1] = [player2X, player2Y]
        app.opposingCoordinates[1] = [player2X + 2.5*app.playerR, player2Y + app.playerR]
    
    #PLAYER 3 movements
    player3 = app.playerCoordinates[2]
    player3X = player3[0]
    player3Y = player3[1]
    opponent3 = app.opposingCoordinates[2]
    opponent3X = opponent3[0]
    opponent3Y = opponent3[1]
    distanceTraveled = 0
    if player3X <= app.width*(0.65):
        startPosition = [player3X, player3Y]
        player3X += (app.width - app.margin - app.playerR - player3X)//(15/app.speed)*(app.playerStaminas[app.playing5[2]]/120)
        player3Y += (app.height*(0.6) + 2*app.playerR - player3Y)//(12/app.speed)*(app.playerStaminas[app.playing5[2]]/120)
        app.playerCoordinates[2] = [player3X, player3Y]
        app.opposingCoordinates[2] = [player3X + 2.5*app.playerR, player3Y - app.playerR]
        distanceTraveled = math.sqrt((player3X - startPosition[0])**2 + (player3Y - startPosition[1])**2)
        app.playerStaminas[app.playing5[2]] = round(app.playerStaminas[app.playing5[2]] - distanceTraveled/240, 1)
        app.opponentStaminas[app.opposing5[2]] = round(app.opponentStaminas[app.opposing5[2]] - distanceTraveled/240, 1)
        for i in range(len(app.playerPercentages[app.playing5[2]])-2):
            if i == 0 or i ==2:
                app.playerPercentages[app.playing5[2]][i] -= 0.002
                app.opponentPercentages[app.opposing5[2]][i] -= 0.002
    elif (app.width*(0.65) <= player3X <= app.width*(0.8) - app.playerR or 
        app.height*(0.6) <= player3Y <= app.height - app.margin - app.playerR): 
        player3X += random.randint(-3,3)
        player3Y += random.randint(-2,3)
        app.playerCoordinates[2] = [player3X, player3Y]
        app.opposingCoordinates[2] = [player3X + 2.5*app.playerR, player3Y - app.playerR]
    
    #PLAYER 4 movements
    player4 = app.playerCoordinates[3]
    player4X = player4[0]
    player4Y = player4[1]
    opponent4 = app.opposingCoordinates[3]
    opponent4X = opponent4[0]
    opponent4Y = opponent4[1]
    distanceTraveled = 0
    if player4X <= app.width*(0.85):
        startPosition = [player4X, player4Y]
        player4X += (app.width - app.margin - app.playerR - player4X)//(10/app.speed)*(app.playerStaminas[app.playing5[3]]/120)
        player4Y -= (player4Y - app.margin - 2*app.playerR)//(11/app.speed)*(app.playerStaminas[app.playing5[3]]/120)
        app.playerCoordinates[3] = [player4X, player4Y]
        app.opposingCoordinates[3] = [player4X + app.playerR, player4Y + 2.5*app.playerR]
        distanceTraveled = math.sqrt((player4X - startPosition[0])**2 + (player4Y - startPosition[1])**2)
        app.playerStaminas[app.playing5[3]] = round(app.playerStaminas[app.playing5[3]] - distanceTraveled/240, 1)
        app.opponentStaminas[app.opposing5[3]] = round(app.opponentStaminas[app.opposing5[3]] - distanceTraveled/240, 1)
        for i in range(len(app.playerPercentages[app.playing5[3]])-2):
            if i == 0 or i ==2:
                app.playerPercentages[app.playing5[3]][i] -= 0.002
                app.opponentPercentages[app.opposing5[3]][i] -= 0.002
    elif (app.width*(0.8) <= player4X <= app.width -  app.margin - 1.4*app.playerR or 
        app.margin + app.playerR <= player4Y <= app.height*(0.45)): 
        player4X += random.randint(-3,3)
        player4Y += random.randint(-3,3)
        app.playerCoordinates[3] = [player4X, player4Y]
        app.opposingCoordinates[3] = [player4X, player4Y + 2.5*app.playerR]

    
    #PLAYER 5 movements
    player5 = app.playerCoordinates[4]
    player5X = player5[0]
    player5Y = player5[1]
    opponent5 = app.opposingCoordinates[4]
    opponent5X = opponent5[0]
    opponent5Y = opponent5[1]
    distanceTraveled = 0
    if player5X <= app.width*(0.85):
        startPosition = [player5X, player5Y]
        player5X += (app.width - app.margin - app.playerR - player5X)//(10/app.speed)*(app.playerStaminas[app.playing5[4]]/120)
        player5Y += (app.height - app.margin - 2*app.playerR - player5Y)//(11/app.speed)*(app.playerStaminas[app.playing5[4]]/120)
        app.playerCoordinates[4] = [player5X, player5Y]
        app.opposingCoordinates[4] = [player5X + app.playerR, player5Y - 2.5*app.playerR]
        distanceTraveled = math.sqrt((player5X - startPosition[0])**2 + (player5Y - startPosition[1])**2)
        app.playerStaminas[app.playing5[4]] = round(app.playerStaminas[app.playing5[4]] - distanceTraveled/240, 1)
        app.opponentStaminas[app.opposing5[4]] = round(app.opponentStaminas[app.opposing5[4]] - distanceTraveled/240, 1)
        for i in range(len(app.playerPercentages[app.playing5[4]])-2):
            if i == 0 or i ==2:
                app.playerPercentages[app.playing5[4]][i] -= 0.002
                app.opponentPercentages[app.opposing5[4]][i] -= 0.002
    elif (app.width*(0.8) <= player5X <= app.width -  app.margin - app.playerR or 
        app.height*0.6 <= player5Y <= app.height - app.margin - 1.4*app.playerR): 
        player5X += random.randint(-3,3)
        player5Y += random.randint(-3,3)
        app.playerCoordinates[4] = [player5X, player5Y]
        app.opposingCoordinates[4] = [player5X, player5Y - 2.5*app.playerR]
    
    for player in app.playerStaminas:
        if app.playerStaminas[player] < 0:
            app.playerStaminas[player] = 0
    
    for opponent in app.opponentStaminas:
        if app.opponentStaminas[opponent] < 0:
            app.opponentStaminas[opponent] = 0

    app.basketballCoordinates = app.playerCoordinates[app.playerWithBall]

def moveBasketball(app):
    passCompletionPercentage = app.playerWithBallPercentages[1] #check if pass is completed based on rating
    randomDecimal = float(random.randrange(0, 80)/100)
    if randomDecimal <= passCompletionPercentage: 
        app.previousPlayerWithBall = app.playerWithBall
        arrangedPlaying5, arrangedOpposing5 = arrangePlayerOveralls(app, app.playing5, app.opposing5)
        randint = random.randrange(0,100)
        if app.possession == 0:
            if 0 <= randint <= 30: #makes sure best player gets more opportunities
                highestOverallPlayer = arrangedPlaying5[1][4]
                newPlayerWithBall = app.playing5.index(highestOverallPlayer)
            elif 31 <= randint <= 55:
                secondOverallPlayer = arrangedPlaying5[1][3]
                newPlayerWithBall = app.playing5.index(secondOverallPlayer)
            elif 56 <= randint <= 73:
                thirdOverallPlayer = arrangedPlaying5[1][2]
                newPlayerWithBall = app.playing5.index(thirdOverallPlayer)
            elif 74 <= randint <= 86:
                fourthOverallPlayer = arrangedPlaying5[1][1]
                newPlayerWithBall = app.playing5.index(fourthOverallPlayer)
            elif 87 <= randint <= 100:
                fifthOverallPlayer = arrangedPlaying5[1][0]
                newPlayerWithBall = app.playing5.index(fifthOverallPlayer)
            basketballX = app.basketballCoordinates[0]
            basketballY = app.basketballCoordinates[1]
            player1X = app.playerCoordinates[app.previousPlayerWithBall][0]
            player1Y = app.playerCoordinates[app.previousPlayerWithBall][1]
            player2X = app.playerCoordinates[newPlayerWithBall][0]
            player2Y = app.playerCoordinates[newPlayerWithBall][1]
            if player1X > player2X:
                basketballX -= (player1X - player2X)
            else:
                basketballX += (player2X - player1X)
            if player1Y > player2Y:
                basketballY -= (player1Y - player2Y)
            else:
                basketballY += (player2Y - player1Y)
            app.basketballCoordinates = [basketballX, basketballY]
            app.playerWithBall = newPlayerWithBall
        else:
            if 0 <= randint <= 30: #makes sure best player gets more opportunities
                highestOverallPlayer = arrangedOpposing5[1][4]
                newPlayerWithBall = app.opposing5.index(highestOverallPlayer)
            elif 31 <= randint <= 55:
                secondOverallPlayer = arrangedOpposing5[1][3]
                newPlayerWithBall = app.opposing5.index(secondOverallPlayer)
            elif 56 <= randint <= 73:
                thirdOverallPlayer = arrangedOpposing5[1][2]
                newPlayerWithBall = app.opposing5.index(thirdOverallPlayer)
            elif 74 <= randint <= 86:
                fourthOverallPlayer = arrangedOpposing5[1][1]
                newPlayerWithBall = app.opposing5.index(fourthOverallPlayer)
            elif 87 <= randint <= 100:
                fifthOverallPlayer = arrangedOpposing5[1][0]
                newPlayerWithBall = app.opposing5.index(fifthOverallPlayer)
            basketballX = app.basketballCoordinates[0]
            basketballY = app.basketballCoordinates[1]
            player1X = app.opposingCoordinates[app.previousPlayerWithBall][0]
            player1Y = app.opposingCoordinates[app.previousPlayerWithBall][1]
            player2X = app.opposingCoordinates[newPlayerWithBall][0]
            player2Y = app.opposingCoordinates[newPlayerWithBall][1]
            if player1X > player2X:
                basketballX += (player1X - player2X)
            else:
                basketballX -= (player2X - player1X)
            if player1Y > player2Y:
                basketballY += (player1Y - player2Y)
            else:
                basketballY -= (player2Y - player1Y)
            app.basketballCoordinates = [basketballX, basketballY]
    else:
        app.possession = 1 - app.possession

def userMadeThree(app):
    app.playerScore += 3                        
    previousPlayerWithBallName = app.playing5[app.previousPlayerWithBall]
    if app.playerWithBallName in app.userStats:
        app.userStats[app.playerWithBallName][0] += 3
    elif app.playerWithBallName in app.teamRoster:
        app.userStats[app.playerWithBallName] = [3,0,0,0,0]
    app.playerFieldGoals[0] += 1
    app.playerFieldGoals[1] += 1
    app.possession = 1 - app.possession
    app.posessionSwitchTime = 0

def userMadeTwo(app):
    app.playerScore += 2
    previousPlayerWithBallName = app.playing5[app.previousPlayerWithBall]
    if app.playerWithBallName in app.userStats:
        app.userStats[app.playerWithBallName][0] += 2
    elif app.playerWithBallName in app.teamRoster:
        app.userStats[app.playerWithBallName] = [2,0,0,0,0]
    if previousPlayerWithBallName in app.userStats:
        app.userStats[previousPlayerWithBallName][2] += 1
    elif app.playerWithBallName in app.teamRoster:
        app.userStats[app.playerWithBallName] = [0,0,1,0,0]
    app.playerFieldGoals[0] += 1
    app.playerFieldGoals[1] += 1
    app.possession = 1 - app.possession
    app.posessionSwitchTime = 0

def userMissThree(app):
    reboundDecimal = float(decimal.Decimal(random.randrange(000, 100))/100)
    reboundOveralls = arrangeReboundOveralls(app, app.opposing5)
    opposingPlayerWithBallName = app.opposing5[app.playerWithBall]
    app.possession = 1 - app.possession
    app.posessionSwitchTime = 0
    app.playerFieldGoals[1] += 1
    if reboundDecimal <= 0.17:
        reboundingPlayer = reboundOveralls[1][4]
        if reboundingPlayer in app.opponentStats:
            app.opponentStats[reboundingPlayer][1] += 1
        elif opposingPlayerWithBallName in app.opposingTeamPlayers:
            app.opponentStats[reboundingPlayer] = [0,1,0,0,0]
    else:
        if opposingPlayerWithBallName in app.opponentStats:
            app.opponentStats[opposingPlayerWithBallName][1] += 1
        elif opposingPlayerWithBallName in app.opposingTeamPlayers:
            app.opponentStats[opposingPlayerWithBallName] = [0,1,0,0,0]

def userMissTwo(app):
    reboundDecimal = float(decimal.Decimal(random.randrange(000, 100))/100)
    reboundOveralls = arrangeReboundOveralls(app, app.opposing5)
    opposingPlayerWithBallName = app.opposing5[app.playerWithBall]
    app.possession = 1 - app.possession
    app.posessionSwitchTime = 0
    app.playerFieldGoals[1] += 1
    if reboundDecimal <= 0.17:
        reboundingPlayer = reboundOveralls[1][4]
        if reboundingPlayer in app.opponentStats:
            app.opponentStats[reboundingPlayer][1] += 1
        elif opposingPlayerWithBallName in app.opposingTeamPlayers:
            app.opponentStats[reboundingPlayer] = [0,1,0,0,0]
    else:
        if opposingPlayerWithBallName in app.opponentStats:
            app.opponentStats[opposingPlayerWithBallName][1] += 1
        elif opposingPlayerWithBallName in app.opposingTeamPlayers:
            app.opponentStats[opposingPlayerWithBallName] = [0,1,0,0,0]

def doStepPlayerShot(app):
    if userShootingDistance(app, app.basketballCoordinates):
        percentageToShoot = app.shotTendency
        shotDecimal = float(decimal.Decimal(random.randrange(000, 100))/100)
        app.playerWithBallName = app.playing5[app.playerWithBall]
        app.playerWithBallPercentages = app.playerPercentages[app.playerWithBallName]
        opposingPlayerWithBallName = app.opposing5[app.playerWithBall] #check for block
        opposingPlayerPercentages = app.opponentPercentages[app.opposing5[app.playerWithBall]]
        blockPercentage = opposingPlayerPercentages[4]
        if shotDecimal <= percentageToShoot:
            shotTypeDecimal = float(decimal.Decimal(random.randrange(000, 100))/100)
            shotMakeDecimal = float(decimal.Decimal(random.randrange(000, 100))/100)
            blockDecimal = float(decimal.Decimal(random.randrange(000, 100))/100)
            if blockDecimal <= blockPercentage:
                if opposingPlayerWithBallName in app.opponentStats:
                    app.opponentStats[opposingPlayerWithBallName][4] += 1
                elif opposingPlayerWithBallName in app.opposingTeamPlayers:
                    app.opponentStats[opposingPlayerWithBallName] = [0,0,0,0,1]
                app.possession = 1 - app.possession
            if shotTypeDecimal <= app.threePointTendency: #shooting a three
                basketballX = app.basketballCoordinates[0]
                basketballY = app.basketballCoordinates[1]
                basketballX += (app.width-app.margin - basketballX)/10
                if basketballY < app.height//2:
                    basketballY += (app.height//2 - basketballY)/10
                else:
                    basketballY -= (basketballY - app.height//2)/10
                app.basketballCoordinates = [basketballX, basketballY]
                if shotMakeDecimal <= app.playerWithBallPercentages[2]:
                    userMadeThree(app)
                else:
                    userMissThree(app)
            else:
                if shotMakeDecimal <= app.playerWithBallPercentages[0]: #shooting a two
                    userMadeTwo(app)
                else:
                    userMissTwo(app)

def doStepOpponentMovements(app): #when CPU posession
    app.posessionSwitchTime += 0.1

    #opponent1 movements
    player1 = app.playerCoordinates[0]
    player1X = player1[0]
    player1Y = player1[1]
    opponent1 = app.opposingCoordinates[0]
    opponent1X = opponent1[0]
    opponent1Y = opponent1[1]
    distanceTraveled = 0
    if opponent1X >= app.width*(0.26):
        startPosition = opponent1X
        opponent1X -= (opponent1X - app.margin - 0.22)//(10/app.speed)*(app.opponentStaminas[app.opposing5[0]]/120)
        app.opposingCoordinates[0][0] = opponent1X
        app.playerCoordinates[0] = [opponent1X - 2.5*app.playerR, opponent1Y]
        distanceTraveled = (startPosition - opponent1X)
        app.playerStaminas[app.playing5[0]] = round(app.playerStaminas[app.playing5[0]] - distanceTraveled/240, 1)
        app.opponentStaminas[app.opposing5[0]] = round(app.opponentStaminas[app.opposing5[0]] - distanceTraveled/240, 1)
        for i in range(len(app.playerPercentages[app.playing5[0]])-2):
            if i == 0 or i ==2:
                app.playerPercentages[app.playing5[0]][i] -= 0.002
                app.opponentPercentages[app.opposing5[0]][i] -= 0.002
    elif (app.width*(0.15) < opponent1X < app.width*(0.22) or 
        app.height*(0.4) < opponent1Y < app.height*(0.6)):
        opponent1X += random.randint(-3,3)
        opponent1Y += random.randint(-3,3)
        app.opposingCoordinates[0] = [opponent1X, opponent1Y]
        app.playerCoordinates[0] = [opponent1X - 2.5*app.playerR, opponent1Y]

    #Opponent 2 movements
    player2 = app.playerCoordinates[1]
    player2X = player2[0]
    player2Y = player2[1]
    opponent2 = app.opposingCoordinates[1]
    opponent2X = opponent2[0]
    opponent2Y = opponent2[1]
    distanceTraveled = 0
    if opponent2X >= app.width*(0.35):
        startPosition = [opponent2X, opponent2Y]
        opponent2X -= (opponent2X - app.margin - app.playerR - 0.35)//(15/app.speed)*(app.opponentStaminas[app.opposing5[1]]/120)
        opponent2Y -= (player2Y - app.height*(0.2) - 2*app.playerR)//(10/app.speed)*(app.opponentStaminas[app.opposing5[1]]/120)
        app.opposingCoordinates[1] = [opponent2X, opponent2Y]
        app.playerCoordinates[1] = [opponent2X - 2.5*app.playerR, opponent2Y]
        distanceTraveled = math.sqrt((startPosition[0] - opponent2X)**2 + (opponent2Y - startPosition[1])**2)
        app.playerStaminas[app.playing5[1]] = round(app.playerStaminas[app.playing5[1]] - distanceTraveled/240, 1)
        app.opponentStaminas[app.opposing5[1]] = round(app.opponentStaminas[app.opposing5[1]] - distanceTraveled/240, 1)
        for i in range(len(app.playerPercentages[app.playing5[1]])-2):
            if i == 0 or i ==2:
                app.playerPercentages[app.playing5[1]][i] -= 0.002
                app.opponentPercentages[app.opposing5[1]][i] -= 0.002
    elif (app.width*(0.2) + app.playerR <= opponent2X <= app.width*0.35 or 
        app.margin + app.playerR <= opponent2Y <= app.height*(0.5)): 
        opponent2X += random.randint(-3,3)
        opponent2Y += random.randint(-3,3)
        app.opposingCoordinates[1] = [opponent2X, opponent2Y]
        app.playerCoordinates[1] = [opponent2X - 2.5*app.playerR, opponent2Y + app.playerR]

    #Opponent 3 movements
    player3 = app.playerCoordinates[2]
    player3X = player3[0]
    player3Y = player3[1]
    opponent3 = app.opposingCoordinates[2]
    opponent3X = opponent3[0]
    opponent3Y = opponent3[1]
    distanceTraveled = 0
    if opponent3X >= app.width*(0.35):
        startPosition = [opponent3X, opponent3Y]
        opponent3X -= (opponent3X - app.margin - app.playerR - 0.35)//(15/app.speed)*(app.opponentStaminas[app.opposing5[2]]/120)
        opponent3Y += (app.height*(0.55) + 2*app.playerR - opponent3Y)//(10/app.speed)*(app.opponentStaminas[app.opposing5[2]]/120)
        app.opposingCoordinates[2] = [opponent3X, opponent3Y]
        app.playerCoordinates[2] = [opponent3X - 2.5*app.playerR, opponent3Y]
        distanceTraveled = math.sqrt((startPosition[0] - opponent3X)**2 + (opponent3Y - startPosition[1])**2)
        app.playerStaminas[app.playing5[2]] = round(app.playerStaminas[app.playing5[2]] - distanceTraveled/240, 1)
        app.opponentStaminas[app.opposing5[2]] = round(app.opponentStaminas[app.opposing5[2]] - distanceTraveled/240, 1)
        for i in range(len(app.playerPercentages[app.playing5[2]])-2):
            if i == 0 or i ==2:
                app.playerPercentages[app.playing5[2]][i] -= 0.002
                app.opponentPercentages[app.opposing5[2]][i] -= 0.002
    elif (app.width*(0.2) + app.playerR <= opponent3X <= app.width*(0.35) or 
        app.height*(0.6) <= opponent3Y <= app.height - app.margin - app.playerR): 
        opponent3X += random.randint(-3,3)
        opponent3Y += random.randint(-3,3)
        app.opposingCoordinates[2] = [opponent3X, opponent3Y]
        app.playerCoordinates[2] = [opponent3X - 2.5*app.playerR, opponent3Y - app.playerR]

    #Opponent 4 movements
    player4 = app.playerCoordinates[3]
    player4X = player4[0]
    player4Y = player4[1]
    opponent4 = app.opposingCoordinates[3]
    opponent4X = opponent4[0]
    opponent4Y = opponent4[1]
    distanceTraveled = 0
    if opponent4X >= app.width*(0.15):
        startPosition = [opponent4X, opponent4Y]
        opponent4X -= (opponent4X - app.margin - 2*app.playerR)//(10/app.speed)*(app.opponentStaminas[app.opposing5[3]]/120)
        opponent4Y -= (opponent4Y - app.margin - 2*app.playerR)//(11/app.speed)*(app.opponentStaminas[app.opposing5[3]]/120)
        app.opposingCoordinates[3] = [opponent4X, opponent4Y]
        app.playerCoordinates[3] = [opponent4X - app.playerR, opponent4Y + 2.5*app.playerR]
        distanceTraveled = math.sqrt((startPosition[0] - opponent4X)**2 + (opponent4Y - startPosition[1])**2)
        app.playerStaminas[app.playing5[3]] = round(app.playerStaminas[app.playing5[3]] - distanceTraveled/240, 1)
        app.opponentStaminas[app.opposing5[3]] = round(app.opponentStaminas[app.opposing5[3]] - distanceTraveled/240, 1)
        for i in range(len(app.playerPercentages[app.playing5[0]])-2):
            if i == 0 or i ==2:
                app.playerPercentages[app.playing5[3]][i] -= 0.002
                app.opponentPercentages[app.opposing5[3]][i] -= 0.002
    elif (app.margin + app.playerR <= opponent4X < app.width*(0.2) or 
        app.margin + app.playerR <= opponent4Y <= app.height*(0.45)): 
        opponent4X += random.randint(-3,3)
        opponent4Y += random.randint(-3,3)
        app.opposingCoordinates[3] = [opponent4X, opponent4Y]
        app.playerCoordinates[3] = [opponent4X, opponent4Y + 2.5*app.playerR]
    
    #Opponent 5 movements
    player5 = app.playerCoordinates[4]
    player5X = player5[0]
    player5Y = player5[1]
    opponent5 = app.opposingCoordinates[4]
    opponent5X = opponent5[0]
    opponent5Y = opponent5[1]
    distanceTraveled = 0
    if opponent5X >= app.width*(0.15):
        startPosition = [opponent5X, opponent5Y]
        opponent5X -= (opponent5X - app.margin - 2*app.playerR)//(10/app.speed)*(app.opponentStaminas[app.opposing5[4]]/120)
        opponent5Y += (app.height - app.margin - 2*app.playerR - opponent5Y)//(11/app.speed)*(app.opponentStaminas[app.opposing5[4]]/120)
        app.opposingCoordinates[4] = [opponent5X, opponent5Y]
        app.playerCoordinates[4] = [opponent5X - app.playerR, opponent5Y - 2.5*app.playerR]
        distanceTraveled = math.sqrt((startPosition[0] - opponent5X)**2 + (opponent5Y - startPosition[1])**2)
        app.playerStaminas[app.playing5[4]] = round(app.playerStaminas[app.playing5[4]] - distanceTraveled/240, 1)
        app.opponentStaminas[app.opposing5[4]] = round(app.opponentStaminas[app.opposing5[4]] - distanceTraveled/240, 1)
        for i in range(len(app.playerPercentages[app.playing5[4]])-2):
            if i == 0 or i ==2:
                app.playerPercentages[app.playing5[4]][i] -= 0.002
                app.opponentPercentages[app.opposing5[4]][i] -= 0.002
    elif (app.margin + app.playerR <= opponent5X < app.width*(0.2) or 
        app.height*0.6 <= opponent5Y <= app.height - app.margin - app.playerR): 
        opponent5X += random.randint(-3,3)
        opponent5Y += random.randint(-3,3)
        app.opposingCoordinates[4] = [opponent5X, opponent5Y]
        app.playerCoordinates[4] = [opponent5X, opponent5Y - 2.5*app.playerR]
    
    for player in app.playerStaminas:
        if app.playerStaminas[player] < 0:
            app.playerStaminas[player] = 0
    
    for opponent in app.opponentStaminas:
        if app.opponentStaminas[opponent] < 0:
            app.opponentStaminas[opponent] = 0

    app.basketballCoordinates = app.opposingCoordinates[app.playerWithBall]

def opponentMadeThree(app):
    app.opponentScore += 3
    previousPlayerWithBallName = app.opposing5[app.previousPlayerWithBall]
    if app.playerWithBallName in app.opponentStats:
        app.opponentStats[app.playerWithBallName][0] += 3
    elif app.playerWithBallName in app.opposingTeamPlayers:
        app.opponentStats[app.playerWithBallName] = [3,0,0,0,0]
    app.opponentFieldGoals[0] += 1
    app.opponentFieldGoals[1] += 1
    app.possession = 1 - app.possession
    app.posessionSwitchTime = 0

def opponentMadeTwo(app):
    app.opponentScore += 2
    previousPlayerWithBallName = app.opposing5[app.previousPlayerWithBall]
    if app.playerWithBallName in app.opponentStats:
        app.opponentStats[app.playerWithBallName][0] += 2
    elif app.playerWithBallName in app.opposingTeamPlayers:
        app.opponentStats[app.playerWithBallName] = [2,0,0,0,0]
    if previousPlayerWithBallName in app.opponentStats:
        app.opponentStats[previousPlayerWithBallName][2] += 1
    elif previousPlayerWithBallName in app.opposingTeamPlayers:
        app.opponentStats[previousPlayerWithBallName] = [0,0,1,0,0]
    app.opponentFieldGoals[0] += 1
    app.opponentFieldGoals[1] += 1
    app.possession = 1 - app.possession
    app.posessionSwitchTime = 0

def opponentMissThree(app):
    reboundDecimal = float(decimal.Decimal(random.randrange(000, 100))/100)
    reboundOveralls = arrangeReboundOveralls(app, app.playing5)
    opposingPlayerWithBallName = app.playing5[app.playerWithBall]
    app.possession = 1 - app.possession
    app.posessionSwitchTime = 0
    app.opponentFieldGoals[1] += 1
    if reboundDecimal <= 0.17:
        reboundingPlayer = reboundOveralls[1][4]
        if reboundingPlayer in app.userStats:
            app.userStats[reboundingPlayer][1] += 1
        elif opposingPlayerWithBallName in app.teamRoster:
            app.userStats[reboundingPlayer] = [0,1,0,0,0]
    else:
        if opposingPlayerWithBallName in app.userStats:
            app.userStats[opposingPlayerWithBallName][1] += 1
        elif opposingPlayerWithBallName in app.teamRoster:
            app.userStats[opposingPlayerWithBallName] = [0,1,0,0,0]

def opponentMissTwo(app):
    reboundDecimal = float(decimal.Decimal(random.randrange(000, 100))/100)
    reboundOveralls = arrangeReboundOveralls(app, app.playing5)
    opposingPlayerWithBallName = app.playing5[app.playerWithBall]
    app.possession = 1 - app.possession
    app.posessionSwitchTime = 0
    app.opponentFieldGoals[1] += 1
    if reboundDecimal <= 0.17:
        reboundingPlayer = reboundOveralls[1][4]
        if reboundingPlayer in app.userStats:
            app.userStats[reboundingPlayer][1] += 1
        elif opposingPlayerWithBallName in app.teamRoster:
            app.userStats[reboundingPlayer] = [0,1,0,0,0]
    else:
        if opposingPlayerWithBallName in app.userStats:
            app.userStats[opposingPlayerWithBallName][1] += 1
        elif opposingPlayerWithBallName in app.teamRoster:
            app.userStats[opposingPlayerWithBallName] = [0,1,0,0,0]

def doStepOpponentShot(app):
    if opponentShootingDistance(app, app.basketballCoordinates):
        percentageToShoot = 0.5
        shotDecimal = float(decimal.Decimal(random.randrange(000, 100))/100)
        app.playerWithBallName = app.opposing5[app.playerWithBall]
        app.playerWithBallPercentages = app.opponentPercentages[app.playerWithBallName]
        opposingPlayerWithBallName = app.playing5[app.playerWithBall] #check for block
        opposingPlayerPercentages = app.playerPercentages[app.playing5[app.playerWithBall]]
        blockPercentage = opposingPlayerPercentages[4]
        if shotDecimal <= percentageToShoot:
            shotTypeDecimal = float(decimal.Decimal(random.randrange(000, 100))/100)
            shotMakeDecimal = float(decimal.Decimal(random.randrange(000, 100))/100)
            blockDecimal = float(decimal.Decimal(random.randrange(000, 100))/100)
            if blockDecimal <= blockPercentage:
                if opposingPlayerWithBallName in app.userStats:
                    app.userStats[opposingPlayerWithBallName][4] += 1
                elif opposingPlayerWithBallName in app.teamRoster:
                    app.userStats[opposingPlayerWithBallName] = [0,0,0,0,1]
                app.possession = 1 - app.possession
            if shotTypeDecimal <= 0.3: #shooting a three
                if shotMakeDecimal <= app.playerWithBallPercentages[2]:
                    opponentMadeThree(app)
                else:
                    opponentMissThree(app)
            else:
                if shotMakeDecimal <= app.playerWithBallPercentages[0]:
                    opponentMadeTwo(app)
                else:
                    opponentMissTwo(app)

def userShootingDistance(app, L):
    x = L[0]
    y = L[1]
    return (math.sqrt(((app.width - app.margin) - x)**2 + ((app.height//2)- y)**2) 
        <= (app.width - app.margin) - app.width*(0.6))

def opponentShootingDistance(app, L):
    x = L[0]
    y = L[1]
    return (math.sqrt((x - app.margin)**2 + ((app.height//2)- y)**2) 
        <= (app.width - app.margin) - app.width*(0.6))

###VIEWERS
def redrawAll(app, canvas):
    if app.gameScreen:
        gameScreen_RedrawAll(app, canvas)
    elif app.teamSelect:
        teamSelectScreen_RedrawAll(app, canvas)
    elif app.rosterScreen:
        rosterScreen_RedrawAll(app, canvas)
        drawRosterScreenComponents(app, canvas)
    elif app.helpScreen:
        helpScreen_RedrawAll(app,canvas)
    elif app.homeScreen:
        homeScreen_RedrawAll(app,canvas)
    elif app.tendenciesScreen:
        tendenciesScreen_RedrawAll(app, canvas)
    elif app.substitutionScreen:
        substitutionScreen_RedrawAll(app, canvas)
    elif app.gameOverScreen:
        gameOverScreen_RedrawAll(app,canvas)
    elif app.playerStatsScreen:
        playerStatsScreen_RedrawAll(app, canvas)
    elif app.opponentStatsScreen:
        opponentStatsScreen_RedrawAll(app, canvas)

#code copied from https://www.cs.cmu.edu/~112/notes/notes-animations-part2.html
def pointInGrid(app, x, y):
    return ((app.margin <= x <= app.width-app.margin) and
            (app.margin <= y <= app.height-app.margin))

#code copied from https://www.cs.cmu.edu/~112/notes/notes-animations-part2.html
def getCell(app, x, y):
    if (not pointInGrid(app, x, y)):
        return
    gridWidth  = app.width - 2*app.margin
    gridHeight = app.height - 2*app.margin
    cellWidth  = gridWidth / app.cols
    cellHeight = gridHeight / app.rows
    row = int((y - app.margin) / cellHeight)
    col = int((x - app.margin) / cellWidth)
    return (row, col)

#check if point is in rectangle (roster screen)
def pointInRect(app, x, y):
    return ((app.width/54 <= x <= app.width*(3/8) and (app.height*(1/6) <= y 
        <= app.height*(21/22))))

#gets the row (roster screen)
def getRow(app, x, y):
    if (not pointInRect(app, x, y)):
        return
    rectWidth = app.width*(3/8) - app.width/54
    rectHeight = app.height*(21/22) - app.height*(1/6)
    cellHeight = rectHeight/app.playersPerTeam
    row = int((y - app.width/54)/ cellHeight) - 2
    return row

def pointInPlaying5Rect(app, x, y):
    return (app.width*(0.4) <= x <= app.width*(53/54) and (app.height*(16/22)
        <= y <= app.height*(21/22)))

def pointInPlayerSelectRect(app, x, y):
    rectWidth = app.width*(53/54) - app.width*(0.4)
    gridWidth = rectWidth/5
    return (app.width*(0.6) <= x <= app.width*(0.6) + gridWidth and app.height*(16/22) <=
        y <= app.height*(21/22))

#gets the col(roster screen)
def getCol(app, x, y):
    if (not pointInPlaying5Rect(app, x, y)):
        return
    rectWidth = app.width*(53/54) - app.width*(0.4)
    rectHeight = app.height*(21/22) - app.height*(16/22)
    cellWidth = rectWidth/5
    col = int((x - app.height*(16/22))/cellWidth)
    return col

################
#BUTTONS
################

def drawBackButton(app, canvas):
    canvas.create_rectangle(app.width/45, app.height*(1/21), app.width/9, 
        app.height*(2/21), fill = 'orange')
    canvas.create_text((app.width/6.5 - app.width/45)//2, app.height*(3/42), 
        text = 'Back', fill = 'white', font = 'Impact 20 bold')

def drawHomeStartButton(app, canvas):
    canvas.create_rectangle(app.width*(2/5), app.height*(4/7),  app.width*(3/5), 
        app.height*(5/7), fill = 'white')
    canvas.create_text(app.width//2, app.height*(9/14), text = 'Start', 
        font = 'Impact 40 bold', fill = 'black')

def drawNextButton(app, canvas):
    canvas.create_rectangle(app.width - app.width/9, app.height*(1/21), 
        app.width - app.width/45, app.height*(2/21), fill = 'orange')
    canvas.create_text(app.width*(24.3/26), app.height*(3/42), text = 'Next',
        fill = 'white',font = 'Impact 20 bold')

def drawHelpButton(app, canvas):
    canvas.create_rectangle(app.width/45, app.height*(19/21), app.width/9, 
        app.height*(20/21), fill = 'orange')
    canvas.create_text((app.width/6.5 - app.width/45)//2, app.height*(39/42), 
        text = 'Help', fill = 'white', font = 'Impact 20 bold')

def drawStartButton(app, canvas):
    canvas.create_rectangle(app.width*(3/5), app.height*(1/13),  app.width*(4/5), 
        app.height*(2/13), fill = 'orange')
    canvas.create_text(app.width*(7/10), app.height*(3/26), text = f'Start/Pause',
        font = 'Impact 30 bold', fill = 'white')

def drawSubButton(app, canvas):
    canvas.create_rectangle(app.width*(1/5), app.height*(11/13),  app.width*(2/5), 
        app.height*(12/13), fill = 'orange')
    canvas.create_text(app.width*(3/10), app.height*(23/26), text = f'Substitution',
        font = 'Impact 30 bold', fill = 'white')

def drawSelectButton(app, canvas):
    canvas.create_rectangle(app.width*(8/9), app.height*(12.5/21), 
        app.width*(43.5/45), app.height*(13.5/21), fill = 'orange')
    canvas.create_text(app.width*(24.1/26), app.height*(26/42), text = 'Select',
        fill = 'white',font = 'Impact 20 bold')

def drawTendenciesButton(app, canvas):
    canvas.create_rectangle(app.width*(3/5), app.height*(11/13),  app.width*(4/5), 
        app.height*(12/13), fill = 'orange')
    canvas.create_text(app.width*(7/10), app.height*(23/26), text = 'Tendencies',
        font = 'Impact 30 bold', fill = 'white')

def drawFastForwardButton(app, canvas):
    canvas.create_rectangle(app.width*(0.85), app.height*(1/13), app.width*(0.9), 
        app.height*(2/13), fill = 'orange')
    canvas.create_text(app.width*(0.875), app.height*(3/26), text = f'x{app.speed}',
        font = 'impact 20 bold', fill = 'white')

def drawPlayerStatsButton(app, canvas):
    canvas.create_rectangle(app.width*(0.24), app.height*(0.83), app.width*(0.36), app.height*(0.88),
        fill = 'blue') 
    canvas.create_text(app.width*(0.3), app.height*(0.855), text = 'Player Stats',
        font = 'impact 20 bold', fill = 'white')

def drawOpponentStatsButton(app, canvas):
    canvas.create_rectangle(app.width*(0.64), app.height*(0.83), app.width*(0.76), app.height*(0.88),
        fill = 'red') 
    canvas.create_text(app.width*(0.7), app.height*(0.855), text = 'Opponent Stats',
        font = 'impact 20 bold', fill = 'white')

###Checks if buttton is clicked
def clickedPlayerStatsButton(app, x, y):
    return (app.width*(0.24) <= x <= app.width*(0.36) and app.height*(0.83) <= 
        y <= app.height*(0.88))

def clickedOpponentStatsButton(app, x, y):
    return (app.width*(0.64) <= x <= app.width*(0.76) and app.height*(0.83) <= 
        y <= app.height*(0.88))

def clickedFastForwardButton(app, x, y):
    return (app.width*(0.85) <= x <= app.width*(0.9) and app.height*(1/13) <= 
        y <= app.height*(2/13))

def clickedBackButton(app, x, y):
    return (app.width/45 <= x <= app.width/9 and app.height*(1/21) <= 
        y <= app.height*(2/21))

def clickedHomeStartButton(app,x,y):
    return (app.width*(2/5) <= x <= app.width*(3/5) and app.height*(4/7)
            <= y <= app.height*(5/7))

def clickedNextButton(app, x, y):
    return (app.width - app.width/9 <= x <= app.width - app.width/45 and 
        app.height*(1/21) <= y <= app.height*(2/21))

def clickedStartButton(app, x, y):
    return (app.width*(3/5) <= x <= app.width*(4/5) and app.height*(1/13) 
        <= y <= app.height*(2/13))

def clickedHelpButton(app, x, y):
    return (app.width/45 <= x <= app.width/9 and app.height*(19/21) 
        <= y <= app.height*(20/21))

def clickedSubButton(app, x, y):
    return (app.width*(1/5) <= x <= app.width*(2/5) and app.height*(11/13)
        <= y <= app.height*(12/13))

def clickedTendenciesButton(app, x, y):
    return (app.width*(3/5) <= x <= app.width*(4/5) and app.height*(11/13)
        <= y <= app.height*(12/13))

def clickedSelectButton(app, x, y):
    return (app.width*(8/9) <= x <= app.width*(43.5/45) and app.height*(12.5/21)
        <= y <= app.height*(13.5/21))

def clickedShotTendencyBar(app, x, y):
    return(app.width*(0.4) <= x <= app.width*(3/4) and app.height/4.2 <= y 
        <= app.height/3.7)

def clickedPassTendencyBar(app, x, y):
    gap = app.height//11
    return(app.width*(0.4) <= x <= app.width*(3/4) and app.height/4.2 + gap <= y 
        <= app.height/3.7 + gap)

def clickedThreePointTendencyBar(app, x, y):
    gap = app.height//11
    return(app.width*(0.4) <= x <= app.width*(3/4) and app.height/4.2 + 2*gap <= y 
        <= app.height/3.7 + 2*gap)

################
#HOME SCREEN
################

def drawTitle(app, canvas):
    canvas.create_text(app.width//2, app.height//3, text = 'NBA Simulator', 
        font = 'Impact 60 bold', fill = 'white')

def drawBasketballTitle(app, canvas):
    canvas.create_oval(app.width//4, app.height//11, app.width*(3/4),
        app.height*(10/11), fill = 'orange', width = 7)
    canvas.create_line(app.width//4, app.height//2, app.width*(3/4),
        app.height//2, width = 7)
    canvas.create_line(app.width//2, app.height//11, app.width//2, 
        app.height*(10/11), width = 7)
    canvas.create_arc(app.width/3, app.height/7, app.width/2.5, app.height*(6/7),
        style = ARC, width = 7, start = 80, extent = -160)
    canvas.create_arc(app.width*(0.6), app.height/7, app.width*(0.7), app.height*(6/7),
        style = ARC, width = 7, start = 106, extent = 148)

def homeScreen_RedrawAll(app, canvas):
    drawBasketballTitle(app, canvas)
    drawTitle(app, canvas)
    drawHelpButton(app, canvas)
    drawHomeStartButton(app, canvas)


################
#HELP SCREEN
################

def drawInstructions(app, canvas):
    canvas.create_rectangle(app.margin, app.margin, app.width - app.margin, 
        app.height - app.margin, fill = 'orange')
    canvas.create_text(app.width//2, app.height//9, text = 'Instructions',
        font = 'Impact 45 bold', fill = 'orange')
    canvas.create_text(app.width//2, app.height//3, 
        text = '1. Select your favorite NBA team to play with' + '\n'
            '2. Rearrange your roster and check the statistics of each player' + '\n'
            '3. Start simulating the game against a random NBA team' + '\n'
            '4. Make substitutions and adjust tendencies to coach your team to a win' + '\n'
            '**ROSTERS ARE FROM 2017-2018 SEASON**'
            , font = 'Impact 30 bold', fill = 'white')
    drawBackButton(app, canvas)

def helpScreen_RedrawAll(app, canvas):
    drawBackButton(app, canvas)
    drawInstructions(app, canvas)

################
#TEAM SELECT SCREEN
################

#code copied from https://www.cs.cmu.edu/~112/notes/notes-animations-part2.html
def getCellBounds(app, row, col):
    gridWidth  = app.width - 2*app.margin
    gridHeight = app.height - 2*app.margin
    cellWidth = gridWidth / app.cols
    cellHeight = gridHeight / app.rows
    x0 = app.margin + col * cellWidth
    x1 = app.margin + (col+1) * cellWidth
    y0 = app.margin + row * cellHeight
    y1 = app.margin + (row+1) * cellHeight
    return (x0, y0, x1, y1)

def drawTeams(app, canvas):
    for row in range(app.rows):
        for col in range(app.cols):
            (x0, y0, x1, y1) = getCellBounds(app, row, col)
            if (row, col) == app.selected:
                canvas.create_rectangle(x0, y0, x1, y1, fill = 'blue')
                canvas.create_text((x0 + x1)/2, (y0 + y1)/2, 
                    text = f'{app.teams[row+col+(5*row)]}', font = 'Impact 15 bold', fill = 'white')
            else:
                canvas.create_rectangle(x0, y0, x1, y1)
                canvas.create_text((x0 + x1)/2, (y0 + y1)/2, 
                    text = f'{app.teams[row+col+(5*row)]}', font = 'Impact 15 bold', fill = 'orange')
    canvas.create_rectangle(app.width/3, app.height*(11/13),  app.width*(2/3), 
        app.height*(12/13), fill = 'orange')
    canvas.create_text(app.width//2, app.height*(23/26), 
        text = f'{app.teams[app.selected[0] + app.selected[1] + (5*app.selected[0])]}',
        font = 'Impact 30 bold', fill = 'white')
    canvas.create_text(app.width//2, app.height*(1/13), text = 'Choose your NBA team',
        font = 'Impact 50 bold', fill = 'orange')

def teamSelectScreen_RedrawAll(app, canvas):
    drawTeams(app, canvas)
    drawBackButton(app, canvas)
    drawNextButton(app, canvas)
    
################
#ROSTER SCREEN
################

def drawPlayerNames(app, canvas):
    rectHeight = app.height*(21/22) - app.height*(1/6)
    lineGap = rectHeight//12
    for j in range(len(app.teamRoster)):
        y1 = app.height*(1/6) + ((j+1)*lineGap) - app.width/46
        overallRating = int(getPlayerRatings(app.teamRoster[j], app.selectedTeamAcronym)[1])
        if app.selectedPlayer == j:
            canvas.create_text(app.width/40, y1, 
                text = app.teamRoster[j], font = 'Impact 15 bold', 
                fill = 'blue', anchor = 'w')
            canvas.create_text(app.width/5, y1, 
                text = f'{overallRating}', font = 'Impact 15 bold', 
                fill = 'blue')
        else:
            canvas.create_text(app.width/40, y1, 
                text = app.teamRoster[j], font = 'Impact 15 bold', 
                fill = 'orange', anchor = 'w')
            canvas.create_text(app.width/5, y1, 
                text = f'{overallRating}', font = 'Impact 15 bold', 
                fill = 'orange')

#filters name for names with 2 spaces or special characters
def filterName(player):
    name = player
    playerName = ''
    for letter in name:
        if letter != '.' and letter != "'":
            playerName += letter
    playerName = playerName.split()
    if len(playerName) == 2:
        firstName = playerName[0]
        lastName = playerName[1]
    elif len(playerName) == 3:
        firstName = playerName[0]
        lastName = playerName[1] + '_' + playerName[2]
    else:
        firstName = playerName[0] + '_' + playerName[1]
        lastName = playerName[2] + '_' + playerName[3] + '_' + playerName[4]
    return firstName, lastName

def drawPlayerImage(app, canvas):
    name = app.teamRoster[app.selectedPlayer]
    firstName, lastName = filterName(name)
    player_api_url = f"https://www.balldontlie.io/api/v1/players?search={firstName}%20{lastName}"
    player_data = requests.get(player_api_url).json()
    
    if player_data['meta']['total_count'] > 0:
        player_id = player_data['data'][0]['id']
        player_image_url = f"https://ak-static.cms.nba.com/wp-content/uploads/headshots/nba/latest/260x190/{player_id}.png"
        response = session.get(player_image_url, stream=True)
        if response.status_code == 200:
            image = Image.open(response.raw)
            image = image.resize((200, 200))
            canvas.create_image(app.width * 0.5, app.height * 0.25, anchor='n', image=ImageTk.PhotoImage(image))
        else:
            print(f"Could not fetch image for player {name}")
    else:
        print(f"Player {name} not found")

def drawPlayerInfo(app, canvas):
    pass

def drawPlayerRatings(app, canvas):
    playerRatings, playerOverall = getPlayerRatings(app.selectedPlayerName, app.selectedTeamAcronym)
    canvas.create_text(app.width*(0.5), app.height*(0.59), 
        text = f'{int(playerOverall)}', font = 'impact 80 bold', 
        fill = 'orange')
    gap = app.width//28
    ratingLegend = ['Scoring:', 'Passing:', 'Three Point:', 'Rebounding:', 'Steal:', 'Block']
    for i in range(len(playerRatings)):
        canvas.create_text(app.width*(0.64), app.height*(0.3)+(i*gap), 
            text = f'{ratingLegend[i]} {playerRatings[i]}', font = 'impact 30 bold',
            fill = 'orange', anchor = 'w')

def drawPlaying5Framework(app, canvas):
    rectWidth = app.width*(53/54) - app.width*(0.4)
    gridWidth = rectWidth/5
    for i in range(5):
        if app.playerToSub == i:
            canvas.create_rectangle(app.width*(0.4) + i*gridWidth, app.height*(16/22), 
                app.width*(0.4) + (i+1)*gridWidth, app.height*(21/22), fill = 'blue')
        else:
            canvas.create_rectangle(app.width*(0.4) + i*gridWidth, app.height*(16/22), 
                app.width*(0.4) + (i+1)*gridWidth, app.height*(21/22))

def drawPlaying5(app, canvas):
    rectWidth = app.width*(53/54) - app.width*(0.4)
    gridWidth = rectWidth/5
    drawPlaying5Framework(app, canvas)
    for j in range(len(app.playing5)):
        firstName, lastName = filterName(app.playing5[j])
        overallRating = app.playing5Overalls[j]
        if app.playerToSub == j:
            canvas.create_text(app.width*(0.4) + gridWidth/2 + j*(gridWidth), app.height*(33/42),
                text = f'{firstName}\n{lastName}', font = 'impact 20 bold', fill = 'white')
            canvas.create_text(app.width*(0.4) + gridWidth/2 + j*(gridWidth), app.height*(36/42),
                text = f'{overallRating}', font = 'impact 30 bold', fill = 'white')
        else:
            canvas.create_text(app.width*(0.4) + gridWidth/2 + j*(gridWidth), app.height*(33/42),
                text = f'{firstName}\n{lastName}', font = 'impact 20 bold', fill = 'blue')
            canvas.create_text(app.width*(0.4) + gridWidth/2 + j*(gridWidth), app.height*(36/42),
                text = f'{overallRating}', font = 'impact 30 bold', fill = 'blue')

def drawRosterScreenComponents(app, canvas):
    canvas.create_text(app.width//2, app.height*(1/12), text = f'{app.selectedTeam} Roster', 
        font = 'Impact 50 bold')
    canvas.create_text(app.width*(0.463), app.height*(15.4/22), text = 'Starting 5',
        font = 'impact 30 bold', fill = 'orange')
    drawBackButton(app, canvas)

def drawRosterScreenFrameWork(app, canvas):
    name = app.selectedPlayerName
    noImageList = ['Jarrell Eddie', 'Glen Clavell', 'Juancho Hernangomez', 'Luc Richard Mbah a Moute',
        'Wayne Selden Jr.', 'Myke Henry', 'Matt Williams Jr,', 'Jordan Crawford', 
        'Mindaugas Kuzminskas', 'Wes Iwundu', 'Danuel House', 'Nazareth Mitrou-Long']
    canvas.create_line(0, app.height*(1/7), app.width, app.height*(1/7), 
        fill = 'orange', width = 5)
    canvas.create_rectangle(app.width/54,app.height*(1/6), app.width*(3/8), 
        app.height*(21/22))
    canvas.create_rectangle(app.width*(0.4), app.height*(1/6),app.width*(53/54),
        app.height*(14.5/22))
    rectHeight = app.height*(21/22) - app.height*(1/6)
    lineGap = rectHeight//12
    for i in range(1, app.playersPerTeam):
        y1 = app.height*(1/6) + (i*lineGap)
        canvas.create_line(app.width/54, y1, app.width*(3/8), y1, width = 1.5)
    canvas.create_text(app.width*(0.7), app.height*(0.21), 
        text = f'{app.teamRoster[app.selectedPlayer]}', font = 'impact 40 bold', 
        fill = 'orange')
    canvas.create_rectangle(app.width*(0.5)-100, app.height*(0.385)-100, 
        app.width*(0.5) + 100, app.height*(0.385) + 100, outline = 'black', width = 2)
    # if name not in noImageList:
        # drawPlayerImage(app, canvas)
    # else:
    canvas.create_text(app.width*0.5, app.height*0.385, text = 'NO IMAGE',
        font = 'Impact 30 bold', fill = 'black')

def rosterScreen_RedrawAll(app, canvas):
    drawRosterScreenFrameWork(app, canvas)
    drawPlayerRatings(app, canvas)
    drawPlayerNames(app, canvas)
    drawNextButton(app,canvas)
    drawSelectButton(app, canvas)
    drawPlaying5(app, canvas)

################
#GAME SCREEN
################

def drawScoreBoard(app, canvas):
    canvas.create_rectangle(app.width/10, app.height/50, app.width/2, app.height*(2/13),
        fill = 'light grey')
    canvas.create_text(app.width/7, app.height*(1.1/13), text = 'Score', 
        font = 'impact 35 bold', fill = 'black')
    canvas.create_text(app.width/4.4, app.height*(0.9/13), text = f'{app.selectedTeam.split()[-1]}',
        font = 'impact 21 bold', fill = 'blue')
    canvas.create_text(app.width/4.4, app.height*(1.35/13), text = f'{app.teams[app.opposingTeam].split()[-1]}',
        font = 'impact 21 bold', fill = 'red')
    canvas.create_text(app.width/3.1, app.height*(1.1/13), text = f'{app.playerScore}',
        font = 'impact 60 bold', fill = 'blue')
    canvas.create_text(app.width/2.7, app.height*(0.95/13), text = ':',
        font = 'impact 60 bold', fill = 'black')
    canvas.create_text(app.width/2.4, app.height*(1.1/13), text = f'{app.opponentScore}',
        font = 'impact 60 bold', fill = 'red')
    
def drawThreePointLine(app, canvas):
    threePointSpace = app.height/20
    courtWidth = app.width - 2*app.margin
    courtHeight = app.height - 2*app.margin
    arcRadius = app.width/4.3
    canvas.create_line(app.margin, app.margin + threePointSpace, 
        app.margin + app.width/20, app.margin + threePointSpace, width = 6)
    canvas.create_line(app.margin, app.height - app.margin - threePointSpace,
        app.margin + app.width/20, app.height - app.margin - threePointSpace, 
        width = 6)
    canvas.create_line(app.margin + courtWidth - app.width/20, 
        app.margin + threePointSpace, app.margin + courtWidth,
        app.margin + threePointSpace, width = 6)
    canvas.create_line(app.margin + courtWidth - app.width/20, 
        app.height - app.margin - threePointSpace, app.margin + courtWidth, 
        app.height - app.margin - threePointSpace, width = 6)
    canvas.create_arc(-app.width/30, app.margin + threePointSpace,
        app.margin + arcRadius, app.margin + courtHeight - threePointSpace,
        style = ARC, width = 6)
    canvas.create_arc(-app.width/30, app.margin + threePointSpace,
        app.margin + arcRadius, app.margin + courtHeight - threePointSpace,
        style = ARC, width = 6, extent = -90)
    canvas.create_arc(-app.width/8 + courtWidth, app.margin + threePointSpace,
        app.margin + arcRadius + courtWidth*(0.88), app.margin + courtHeight - threePointSpace,
        style = ARC, width = 6, start = 90, extent = 180)
    drawInsideThreePointLine(app, canvas)

def drawInsideThreePointLine(app, canvas):
    courtHeight = app.height - 2*app.margin
    courtWidth = app.width - 2*app.margin
    smallArcR = app.width/15
    canvas.create_rectangle(app.margin, app.margin + courtHeight/3,
        app.margin + courtWidth/7, app.margin + courtHeight*(2/3), width = 6)
    canvas.create_rectangle(app.margin + courtWidth*(6/7), app.margin + courtHeight/3,
        app.margin + courtWidth, app.margin + courtHeight*(2/3), width = 6)
    canvas.create_arc(app.margin + courtWidth/7 - smallArcR, app.margin + courtHeight/3,
        app.margin + courtWidth/7 + smallArcR, app.margin + courtHeight*(2/3),
        style = ARC, width = 6, start = 90, extent = -180)
    canvas.create_arc(app.width - app.margin- courtWidth/7 - smallArcR, app.margin + courtHeight/3,
        app.margin + courtWidth - courtWidth/7 + smallArcR, app.margin + courtHeight*(2/3),
        style = ARC, width = 6, start = 90, extent = 180)

def drawCourt(app, canvas):
    courtWidth = app.width - 2*app.margin
    canvas.create_rectangle(app.margin, app.margin, app.width - app.margin, 
        app.height - app.margin, fill = 'light goldenrod', width = 6)
    canvas.create_line(app.width//2,  app.margin, app.width//2, 
        app.height - app.margin, width = 7)
    canvas.create_oval(app.width//2 - app.courtR, app.height//2 - app.courtR, 
        app.width//2 + app.courtR, app.height//2 + app.courtR, width = 7)
    drawThreePointLine(app, canvas)
    drawInsideThreePointLine(app, canvas)
    
def drawUserPlayers(app, canvas):
    for i in range(len(app.playerCoordinates)):
        name = app.playing5[i]
        cx = app.playerCoordinates[i][0]
        cy = app.playerCoordinates[i][1]
        canvas.create_oval(cx - app.playerR, cy - app.playerR, cx + app.playerR, 
            cy + app.playerR, fill = 'blue')
        canvas.create_text(cx, cy, text = f'{name}', font = 'Arial 12 bold',
            fill = 'white', width = 3*app.playerR)

def drawOpposingPlayers(app, canvas):
    for i in range(len(app.opposingCoordinates)):
        name = app.opposing5[i]
        cx = app.opposingCoordinates[i][0]
        cy = app.opposingCoordinates[i][1]
        canvas.create_oval(cx - app.playerR, cy - app.playerR, cx + app.playerR, 
            cy + app.playerR, fill = 'red')
        canvas.create_text(cx, cy, text = f'{name}', font = 'Arial 12 bold',
            fill = 'white', width = 3*app.playerR)

def drawBasketball(app, canvas):
    cx = app.basketballCoordinates[0]
    cy = app.basketballCoordinates[1]
    canvas.create_oval(cx - app.basketballR, cy - app.basketballR, cx + app.basketballR,
        cy + app.basketballR, fill = 'orange', width = 2)
    canvas.create_line(cx, cy-app.basketballR, cx, cy+app.basketballR, width = 2)
    canvas.create_line(cx - app.basketballR, cy, cx + app.basketballR, cy, width = 2)
    canvas.create_arc(cx - 2*app.basketballR, cy - app.basketballR, cx - 0.3*app.basketballR, 
        cy + app.basketballR, style = ARC, width = 2, start = 50, extent = -105)
    canvas.create_arc(cx + 0.3*app.basketballR, cy - app.basketballR, cx + 2*app.basketballR, 
        cy + app.basketballR, style = ARC, width = 2, start = 125, extent = 110)

def drawTime(app, canvas):
    canvas.create_text(app.width/2, app.height*(6.05/7), text = f'Q{app.quarter}', 
        font = 'Impact 40 bold', fill = 'black')
    canvas.create_text(app.width/2, app.height*(6.5/7), text = f'{app.time}', 
        font = 'Impact 40 bold', fill = 'black')

def gameScreen_RedrawAll(app, canvas):
    drawStartButton(app, canvas)
    drawSubButton(app, canvas)
    drawThreePointLine(app, canvas)
    drawCourt(app, canvas)
    drawTime(app, canvas)
    drawTendenciesButton(app, canvas)
    drawScoreBoard(app, canvas)
    drawUserPlayers(app, canvas)
    drawOpposingPlayers(app, canvas)
    drawBasketball(app, canvas)
    drawFastForwardButton(app, canvas)
    

################
#SUBSTITUTION SCREEN
################
def drawStaminas(app, canvas):
    rectHeight = app.height*(21/22) - app.height*(1/6)
    gap = rectHeight//12
    for i in range(len(app.teamRoster)):
        y1 = app.height*(1/6) + ((i+1)*gap) - app.width/46
        playerStamina = app.playerStaminas[app.teamRoster[i]]
        if app.selectedPlayer == i:
            canvas.create_text(app.width*(0.29), y1, 
                text = f'Stamina: {playerStamina}', font = 'Impact 15 bold', 
                fill = 'blue')
        else:
            canvas.create_text(app.width*(0.29), y1, 
                text = f'Stamina:  {playerStamina}', font = 'Impact 15 bold', 
                fill = 'orange')

def drawStaminaOnCourt5(app, canvas):
    rectWidth = app.width*(53/54) - app.width*(0.4)
    gridWidth = rectWidth/5
    for i in range(len(app.playing5)):
        stamina = app.playerStaminas[app.playing5[i]]
        if app.playerToSub == i:
            canvas.create_text(app.width*(0.4) + gridWidth/2 + i*(gridWidth), app.height*(38/42),
                text = f'Stamina: {stamina}', font = 'impact 15', fill = 'white')
        else:
            canvas.create_text(app.width*(0.4) + gridWidth/2 + i*(gridWidth), app.height*(38/42),
                text = f'Stamina: {stamina}', font = 'impact 15', fill = 'blue')

def substitutionScreen_RedrawAll(app, canvas):
    rosterScreen_RedrawAll(app, canvas)
    drawStaminas(app,canvas)
    drawStaminaOnCourt5(app, canvas)
    canvas.create_text(app.width*(0.463), app.height*(15.4/22), text = 'On the Court',
        font = 'impact 30 bold', fill = 'orange')
    canvas.create_text(app.width//2, app.height*(1/12), text = f'Make Substitutions', 
        font = 'Impact 50 bold')


################
#TENDENCIES SCREEN
################

def tendenciesScreen_RedrawAll(app, canvas):
    canvas.create_text(app.width//2, app.height/12, text = 'Tendencies', 
        font = 'Impact 50 bold', fill = 'orange')
    drawBackButton(app, canvas)
    gap = app.height//11

    #shot tendency
    canvas.create_text(app.width//10, app.height/4, text = 'Shooting Tendency:', 
        font = 'Impact 35 bold', fill = 'black', anchor = 'w')
    canvas.create_rectangle(app.width*(0.4), app.height/4.2, app.width*(3/4), 
        app.height/3.7, fill = 'white', width = 2, outline = 'orange')
    canvas.create_text(app.width*(0.8), app.height/4, text = int(app.shotTendency*100), 
        font = 'Impact 30 bold', fill = 'black')
    canvas.create_line(app.width*(0.4), app.height/3.9, app.shotTendencyX, 
        app.height/3.9, width = 8)

    #pass tendency
    canvas.create_text(app.width//10, app.height/4 + gap, text = 'Passing Tendency:', 
        font = 'Impact 35 bold', fill = 'black', anchor = 'w')
    canvas.create_rectangle(app.width*(0.4), app.height/4.2 + gap, app.width*(3/4), 
        app.height/3.7 + gap, fill = 'white', width = 2, outline = 'orange')
    canvas.create_text(app.width*(0.8), app.height/4 + gap, text = int(app.passTendency*100), 
        font = 'Impact 30 bold', fill = 'black')
    canvas.create_line(app.width*(0.4), app.height/3.9 + gap, app.passTendencyX, 
        app.height/3.9 + gap, width = 8)

    #three point tendency
    canvas.create_text(app.width//10, app.height/4 + 2*gap, text = 'Three Point Tendency:', 
        font = 'Impact 35 bold', fill = 'black', anchor = 'w')
    canvas.create_rectangle(app.width*(0.4), app.height/4.2 + 2*gap, app.width*(3/4), 
        app.height/3.7 + 2*gap, fill = 'white', width = 2, outline = 'orange')
    canvas.create_text(app.width*(0.8), app.height/4 + 2*gap, text = int(app.threePointTendency*100), 
        font = 'Impact 30 bold', fill = 'black')
    canvas.create_line(app.width*(0.4), app.height/3.9 + 2*gap, app.threePointTendencyX, 
        app.height/3.9 + 2*gap, width = 8)
    

################
#GAMEOVER SCREEN
################
def drawScores(app, canvas):
    canvas.create_text(app.width*(0.25), app.height*(0.25), text = f'{app.selectedTeam}', 
        font = 'impact 30 bold', fill = 'blue')
    canvas.create_text(app.width*(0.75), app.height*(0.25), text = f'{app.opposingTeamName}', 
        font = 'impact 30 bold', fill = 'red')

def drawUserAnalysis(app, canvas):
    canvas.create_line(app.width*(0.45), app.height*(0.3), app.width*(0.45), app.height*(0.75), width = 3)
    userTeamPoints = 0
    userTeamRebounds = 0
    userTeamAssists = 0
    userTeamSteals = 0
    userTeamBlocks = 0
    userFieldGoalPercentage = round(app.playerFieldGoals[0]/app.playerFieldGoals[1],1)*100
    for player in app.userStats:
        userTeamPoints += app.userStats[player][0]
        userTeamRebounds += app.userStats[player][1]
        userTeamAssists += app.userStats[player][2]
        userTeamSteals += app.userStats[player][3]
        userTeamBlocks += app.userStats[player][4]
    barRadius = app.height//40

    #points
    canvas.create_text(app.width//2, app.height*(0.35), text = 'Team Points',
        font = 'impact 17 bold', fill = 'black')
    canvas.create_rectangle(app.width*(0.45) - (app.width//90)*userTeamPoints, app.height*(0.35) - barRadius,
        app.width*(0.45), app.height*(0.35) + barRadius, fill = 'blue')
    canvas.create_text(app.width*(0.45) - (app.width//90)*(userTeamPoints+0.5), app.height*(0.35), 
        text = f'{userTeamPoints}', font = 'impact 15 bold', fill = 'blue')
    
    #rebounds
    canvas.create_text(app.width//2, app.height*(0.42), text = 'Team Rebounds',
        font = 'impact 17 bold', fill = 'black')
    canvas.create_rectangle(app.width*(0.45) - (app.width//90)*userTeamRebounds, app.height*(0.42) - barRadius,
        app.width*(0.45), app.height*(0.42) + barRadius, fill = 'blue')
    canvas.create_text(app.width*(0.45) - (app.width//90)*(userTeamRebounds+0.5), app.height*(0.42), 
        text = f'{userTeamRebounds}', font = 'impact 15 bold', fill = 'blue')
    
    #assists
    canvas.create_text(app.width//2, app.height*(0.49), text = 'Team Assists',
        font = 'impact 17 bold', fill = 'black')
    canvas.create_rectangle(app.width*(0.45) - (app.width//70)*userTeamAssists, app.height*(0.49) - barRadius,
        app.width*(0.45), app.height*(0.49) + barRadius, fill = 'blue')
    canvas.create_text(app.width*(0.45) - (app.width//70)*(userTeamAssists+0.5), app.height*(0.49), 
        text = f'{userTeamAssists}', font = 'impact 15 bold', fill = 'blue')
    
    #steals
    canvas.create_text(app.width//2, app.height*(0.56), text = 'Team Steals',
        font = 'impact 17 bold', fill = 'black')
    canvas.create_rectangle(app.width*(0.45) - (app.width//70)*userTeamSteals, app.height*(0.56) - barRadius,
        app.width*(0.45), app.height*(0.56) + barRadius, fill = 'blue')
    canvas.create_text(app.width*(0.45) - (app.width//70)*(userTeamSteals+0.5), app.height*(0.56), 
        text = f'{userTeamSteals}', font = 'impact 15 bold', fill = 'blue')
    
    #blocks
    canvas.create_text(app.width//2, app.height*(0.63), text = 'Team Blocks',
        font = 'impact 17 bold', fill = 'black')
    canvas.create_rectangle(app.width*(0.45) - (app.width//70)*userTeamBlocks, app.height*(0.63) - barRadius,
        app.width*(0.45), app.height*(0.63) + barRadius, fill = 'blue')
    canvas.create_text(app.width*(0.45) - (app.width//70)*(userTeamBlocks+0.5), app.height*(0.63), 
        text = f'{userTeamBlocks}', font = 'impact 15 bold', fill = 'blue')
    
    #FG
    canvas.create_text(app.width//2, app.height*(0.7), text = 'Field Goal %',
        font = 'impact 17 bold', fill = 'black')
    canvas.create_text(app.width*(0.41), app.height*(0.7), 
        text = f'{userFieldGoalPercentage}%', font = 'impact 25 bold', fill = 'blue')

def drawOpponentAnalysis(app, canvas):
    canvas.create_line(app.width*(0.55), app.height*(0.3), app.width*(0.55), app.height*(0.75), width = 3)
    opponentTeamPoints = 0
    opponentTeamRebounds = 0
    opponentTeamAssists = 0
    opponentTeamSteals = 0
    opponentTeamBlocks = 0
    opponentFieldGoalPercentage = round(app.opponentFieldGoals[0]/app.opponentFieldGoals[1],1)*100
    for player in app.opponentStats:
        opponentTeamPoints += app.opponentStats[player][0]
        opponentTeamRebounds += app.opponentStats[player][1]
        opponentTeamAssists += app.opponentStats[player][2]
        opponentTeamSteals += app.opponentStats[player][3]
        opponentTeamBlocks += app.opponentStats[player][4]
    barRadius = app.height//40

    #points
    canvas.create_rectangle(app.width*(0.55), app.height*(0.35) - barRadius,
        app.width*(0.55) + (app.width//90)*opponentTeamPoints, app.height*(0.35) + barRadius, fill = 'red')
    canvas.create_text(app.width*(0.55) + (app.width//90)*(opponentTeamPoints+0.7), app.height*(0.35), 
        text = f'{opponentTeamPoints}', font = 'impact 15 bold', fill = 'red')
    
    #rebounds
    canvas.create_rectangle(app.width*(0.55), app.height*(0.42) - barRadius,
        app.width*(0.55) + (app.width//90)*opponentTeamRebounds, app.height*(0.42) + barRadius, fill = 'red')
    canvas.create_text(app.width*(0.55) + (app.width//90)*(opponentTeamRebounds+0.7), app.height*(0.42), 
        text = f'{opponentTeamRebounds}', font = 'impact 15 bold', fill = 'red')
    
    #Assists
    canvas.create_rectangle(app.width*(0.55), app.height*(0.49) - barRadius,
        app.width*(0.55) + (app.width//70)*opponentTeamAssists, app.height*(0.49) + barRadius, fill = 'red')
    canvas.create_text(app.width*(0.55) + (app.width//70)*(opponentTeamAssists+0.5), app.height*(0.49), 
        text = f'{opponentTeamAssists}', font = 'impact 15 bold', fill = 'red')
    
    #steals
    canvas.create_rectangle(app.width*(0.55), app.height*(0.56) - barRadius,
        app.width*(0.55) + (app.width//70)*opponentTeamSteals, app.height*(0.56) + barRadius, fill = 'red')
    canvas.create_text(app.width*(0.55) + (app.width//70)*(opponentTeamSteals+0.5), app.height*(0.56), 
        text = f'{opponentTeamSteals}', font = 'impact 15 bold', fill = 'red')
    
    #blocks
    canvas.create_rectangle(app.width*(0.55), app.height*(0.63) - barRadius,
        app.width*(0.55) + (app.width//70)*opponentTeamBlocks, app.height*(0.63) + barRadius, fill = 'red')
    canvas.create_text(app.width*(0.55) + (app.width//70)*(opponentTeamBlocks+0.5), app.height*(0.63), 
        text = f'{opponentTeamBlocks}', font = 'impact 15 bold', fill = 'red')
    
    #FG
    canvas.create_text(app.width*(0.59), app.height*(0.7), 
        text = f'{opponentFieldGoalPercentage}%', font = 'impact 25 bold', fill = 'red')

def gameOverScreen_RedrawAll(app, canvas):
    canvas.create_text(app.width//2, app.height//11, text = f'The Winner is...',
        font = 'impact 50 bold', fill = 'black')
    canvas.create_text(app.width//2, app.height//6, text = f'The {app.winner}',
        font = 'impact 50 bold', fill = 'orange')
    canvas.create_text(app.width//2, app.height*(0.94), text = 'Press R to restart',
        font = 'impact 29 bold', fill = 'black')
    drawPlayerStatsButton(app, canvas)
    drawOpponentStatsButton(app, canvas)
    drawScores(app, canvas)
    drawUserAnalysis(app, canvas)
    drawOpponentAnalysis(app, canvas)


################
#playerStats SCREEN
################
def drawStatsScreenFramework(app, canvas):
    name = app.selectedPlayerName
    canvas.create_line(0, app.height*(1/7), app.width, app.height*(1/7), 
        fill = 'orange', width = 5)
    canvas.create_rectangle(app.width/54,app.height*(1/6), app.width*(3/8), 
        app.height*(21/22))
    canvas.create_rectangle(app.width*(0.4), app.height*(1/6),app.width*(53/54),
        app.height*(21/22))
    rectHeight = app.height*(21/22) - app.height*(1/6)
    lineGap = rectHeight//12
    for i in range(1, app.playersPerTeam):
        y1 = app.height*(1/6) + (i*lineGap)
        canvas.create_line(app.width/54, y1, app.width*(3/8), y1, width = 1.5)

def drawUserStats(app, canvas):
    canvas.create_line(app.width*(0.45), app.height*(0.27), app.width*(0.45), app.height*(19/22),
        width = 3)
    canvas.create_line(app.width*(0.45), app.height*(19/22), app.width*(50/54), app.height*(19/22),
        width = 3)
    player = app.teamRoster[app.selectedPlayer]
    if player in app.userStats:
        points = app.userStats[player][0]
        rebounds = app.userStats[player][1]
        assists = app.userStats[player][2]
        steals = app.userStats[player][3]
        blocks = app.userStats[player][4]
    else:
        points = 0
        rebounds = 0
        assists = 0
        steals = 0
        blocks = 0
    canvas.create_text(app.width*(0.5), app.height*(19.5/22), text = 'Points',
        font = 'impact 15 bold')
    canvas.create_text(app.width*(0.6), app.height*(19.5/22), text = 'Rebounds',
        font = 'impact 15 bold')
    canvas.create_text(app.width*(0.7), app.height*(19.5/22), text = 'Assists',
        font = 'impact 15 bold')
    canvas.create_text(app.width*(0.8), app.height*(19.5/22), text = 'Steals',
        font = 'impact 15 bold')
    canvas.create_text(app.width*(0.9), app.height*(19.5/22), text = 'Blocks',
        font = 'impact 15 bold')
    barRadius = app.width*(0.015)

    #points
    canvas.create_rectangle(app.width*(0.5) - barRadius, app.height*(19/22) - (app.height//25)*points,
        app.width*(0.5) + barRadius, app.height*(19/22), fill = 'black')
    canvas.create_text(app.width*(0.5), app.height*(19/22) - (app.height//25)*(points+0.5), text = f'{points}',
        font = 'impact 20 bold', fill = 'black')

    #rebounds
    canvas.create_rectangle(app.width*(0.6) - barRadius, app.height*(19/22) - (app.height//25)*rebounds,
        app.width*(0.6) + barRadius, app.height*(19/22), fill = 'black')
    canvas.create_text(app.width*(0.6), app.height*(19/22) - (app.height//25)*(rebounds+0.5), text = f'{rebounds}',
        font = 'impact 20 bold', fill = 'black')
    
    #assists
    canvas.create_rectangle(app.width*(0.7) - barRadius, app.height*(19/22) - (app.height//25)*assists,
        app.width*(0.7) + barRadius, app.height*(19/22), fill = 'black')
    canvas.create_text(app.width*(0.7), app.height*(19/22) - (app.height//25)*(assists+0.5), text = f'{assists}',
        font = 'impact 20 bold', fill = 'black')
    
    #steals
    canvas.create_rectangle(app.width*(0.8) - barRadius, app.height*(19/22) - (app.height//25)*steals,
        app.width*(0.8) + barRadius, app.height*(19/22), fill = 'black')
    canvas.create_text(app.width*(0.8), app.height*(19/22) - (app.height//25)*(steals+0.5), text = f'{steals}',
        font = 'impact 20 bold', fill = 'black')
    
    #blocks
    canvas.create_rectangle(app.width*(0.9) - barRadius, app.height*(19/22) - (app.height//25)*blocks,
        app.width*(0.9) + barRadius, app.height*(19/22), fill = 'black')
    canvas.create_text(app.width*(0.9), app.height*(19/22) - (app.height//25)*(blocks+0.5), text = f'{blocks}',
        font = 'impact 20 bold', fill = 'black')
            
def playerStatsScreen_RedrawAll(app, canvas):
    canvas.create_text(app.width//2, app.height*(1/12), text = f'Player Statistics', 
        font = 'Impact 50 bold')
    canvas.create_text(app.width*(0.7), app.height*(0.21), 
        text = f'{app.teamRoster[app.selectedPlayer]}', font = 'impact 40 bold', 
        fill = 'orange')
    drawStatsScreenFramework(app, canvas)
    drawPlayerNames(app, canvas)
    drawUserStats(app, canvas)
    drawBackButton(app, canvas)


################
#OpponentStats SCREEN
################

def drawOpponentStats(app, canvas):
    canvas.create_line(app.width*(0.45), app.height*(0.27), app.width*(0.45), app.height*(19/22),
        width = 3)
    canvas.create_line(app.width*(0.45), app.height*(19/22), app.width*(50/54), app.height*(19/22),
        width = 3)
    player = app.opposingTeamPlayers[app.selectedPlayer]
    if player in app.opponentStats:
        points = app.opponentStats[player][0]
        rebounds = app.opponentStats[player][1]
        assists = app.opponentStats[player][2]
        steals = app.opponentStats[player][3]
        blocks = app.opponentStats[player][4]
    else:
        points = 0
        rebounds = 0
        assists = 0
        steals = 0
        blocks = 0
    canvas.create_text(app.width*(0.5), app.height*(19.5/22), text = 'Points',
        font = 'impact 15 bold')
    canvas.create_text(app.width*(0.6), app.height*(19.5/22), text = 'Rebounds',
        font = 'impact 15 bold')
    canvas.create_text(app.width*(0.7), app.height*(19.5/22), text = 'Assists',
        font = 'impact 15 bold')
    canvas.create_text(app.width*(0.8), app.height*(19.5/22), text = 'Steals',
        font = 'impact 15 bold')
    canvas.create_text(app.width*(0.9), app.height*(19.5/22), text = 'Blocks',
        font = 'impact 15 bold')
    barRadius = app.width*(0.015)

    #points
    canvas.create_rectangle(app.width*(0.5) - barRadius, app.height*(19/22) - (app.height//25)*points,
        app.width*(0.5) + barRadius, app.height*(19/22), fill = 'black')
    canvas.create_text(app.width*(0.5), app.height*(19/22) - (app.height//25)*(points+0.5), text = f'{points}',
        font = 'impact 20 bold', fill = 'black')

    #rebounds
    canvas.create_rectangle(app.width*(0.6) - barRadius, app.height*(19/22) - (app.height//25)*rebounds,
        app.width*(0.6) + barRadius, app.height*(19/22), fill = 'black')
    canvas.create_text(app.width*(0.6), app.height*(19/22) - (app.height//25)*(rebounds+0.5), text = f'{rebounds}',
        font = 'impact 20 bold', fill = 'black')
    
    #assists
    canvas.create_rectangle(app.width*(0.7) - barRadius, app.height*(19/22) - (app.height//25)*assists,
        app.width*(0.7) + barRadius, app.height*(19/22), fill = 'black')
    canvas.create_text(app.width*(0.7), app.height*(19/22) - (app.height//25)*(assists+0.5), text = f'{assists}',
        font = 'impact 20 bold', fill = 'black')
    
    #steals
    canvas.create_rectangle(app.width*(0.8) - barRadius, app.height*(19/22) - (app.height//25)*steals,
        app.width*(0.8) + barRadius, app.height*(19/22), fill = 'black')
    canvas.create_text(app.width*(0.8), app.height*(19/22) - (app.height//25)*(steals+0.5), text = f'{steals}',
        font = 'impact 20 bold', fill = 'black')
    
    #blocks
    canvas.create_rectangle(app.width*(0.9) - barRadius, app.height*(19/22) - (app.height//25)*blocks,
        app.width*(0.9) + barRadius, app.height*(19/22), fill = 'black')
    canvas.create_text(app.width*(0.9), app.height*(19/22) - (app.height//25)*(blocks+0.5), text = f'{blocks}',
        font = 'impact 20 bold', fill = 'black')

def drawOpponentNames(app, canvas):
    rectHeight = app.height*(21/22) - app.height*(1/6)
    lineGap = rectHeight//12
    for j in range(len(app.teamRoster)):
        y1 = app.height*(1/6) + ((j+1)*lineGap) - app.width/46
        overallRating = int(getPlayerRatings(app.opposingTeamPlayers[j], app.opposingTeam)[1])
        if app.selectedPlayer == j:
            canvas.create_text(app.width/40, y1, 
                text = app.opposingTeamPlayers[j], font = 'Impact 15 bold', 
                fill = 'blue', anchor = 'w')
            canvas.create_text(app.width/5, y1, 
                text = f'{overallRating}', font = 'Impact 15 bold', 
                fill = 'blue')
        else:
            canvas.create_text(app.width/40, y1, 
                text = app.opposingTeamPlayers[j], font = 'Impact 15 bold', 
                fill = 'orange', anchor = 'w')
            canvas.create_text(app.width/5, y1, 
                text = f'{overallRating}', font = 'Impact 15 bold', 
                fill = 'orange')

def opponentStatsScreen_RedrawAll(app, canvas):
    canvas.create_text(app.width//2, app.height*(1/12), text = f'Opponent Statistics', 
        font = 'Impact 50 bold')
    canvas.create_text(app.width*(0.7), app.height*(0.21), 
        text = f'{app.opposingTeamPlayers[app.selectedPlayer]}', font = 'impact 40 bold', 
        fill = 'orange')
    drawStatsScreenFramework(app, canvas)
    drawOpponentNames(app, canvas)
    drawOpponentStats(app, canvas)
    drawBackButton(app, canvas)

    
runApp(width=1300, height=750)


