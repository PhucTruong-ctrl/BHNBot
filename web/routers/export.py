from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
import pandas as pd
import io
from datetime import datetime

from ..database import fetchall

from ..dependencies import require_admin

router = APIRouter(dependencies=[Depends(require_admin)])

@router.get("/users")
async def export_users_excel():
    """Export user list to Excel with Risk Score."""
    
    # 1. Fetch data
    users = await fetchall("""
        SELECT 
            u.user_id, 
            u.username, 
            u.seeds as balance, 
            u.last_daily,
            u.last_chat_reward,
            COALESCE(SUM(CASE WHEN s.stat_key = 'total_fish_caught' THEN s.value ELSE 0 END), 0) as total_fish
        FROM users u
        LEFT JOIN user_stats s ON u.user_id = s.user_id
        GROUP BY u.user_id
    """)
    
    if not users:
        raise HTTPException(status_code=404, detail="No users found")

    # 2. Process with Pandas
    df = pd.DataFrame(users)
    
    # Convert dates
    df['last_activity'] = pd.to_datetime(
        df['last_daily'].combine_first(df['last_chat_reward'])
    )
    
    # Calculate Risk Score (Heuristic)
    # Risk = (Balance / Median) * Log(Total Fish + 1) ? 
    # Simplify: If Balance > 100k and Fish < 10 -> High Risk (Cheater?)
    median_balance = df['balance'].median()
    if median_balance == 0: median_balance = 1
    
    def calc_risk(row):
        score = 0
        # High Balance flag
        if row['balance'] > median_balance * 10:
            score += 3
        # Low activity but high balance
        if row['balance'] > 5000 and row['total_fish'] < 5:
            score += 5
        return score

    df['risk_score'] = df.apply(calc_risk, axis=1)
    
    # Rename for export
    export_df = df[[
        'user_id', 'username', 'balance', 'total_fish', 'last_activity', 'risk_score'
    ]].rename(columns={
        'user_id': 'User ID',
        'username': 'Username',
        'balance': 'Balance (Hạt)',
        'total_fish': 'Fish Caught',
        'last_activity': 'Last Active',
        'risk_score': 'Risk Score'
    })

    # 3. Create Excel file in memory
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        export_df.to_excel(writer, index=False, sheet_name='Users')
    
    output.seek(0)
    
    headers = {
        'Content-Disposition': f'attachment; filename="users_export_{datetime.now().strftime("%Y%m%d")}.xlsx"'
    }
    
    return StreamingResponse(
        output, 
        headers=headers, 
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
