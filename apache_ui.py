# Apache Log Analysis Tab Component
# Add this after the main imports in code.py

import plotly.graph_objects as go
import plotly.express as px

def render_apache_analysis(apache_data):
    """Render Apache log analysis with charts and metrics"""
    import json
    
    try:
        data = json.loads(apache_data)
        
        if "error" in data:
            st.error(f"❌ {data['error']}")
            return
        
        # Summary metrics in columns
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Total Requests", 
                f"{data['summary']['total_requests']:,}",
                help="Total number of HTTP requests analyzed"
            )
        
        with col2:
            st.metric(
                "Avg Response Time",
                f"{data['summary']['avg_response_time_ms']:.0f} ms",
                help="Average response time across all requests"
            )
        
        with col3:
            st.metric(
                "P95 Response Time",
                f"{data['summary']['p95_response_time_ms']:,} ms",
                help="95th percentile response time"
            )
        
        with col4:
            error_rate = data['summary']['error_rate_percent']
            st.metric(
                "Error Rate",
                f"{error_rate:.2f}%",
                delta=f"{'🔴' if error_rate > 5 else '🟢'}",
                help="Percentage of 4xx and 5xx errors"
            )
        
        st.divider()
        
        # Charts row 1: Status codes and Response time distribution
        chart_col1, chart_col2 = st.columns(2)
        
        with chart_col1:
            st.subheader("📊 Status Code Distribution")
            status_data = data['status_codes']
            fig_status = go.Figure(data=[go.Pie(
                labels=['2xx Success', '4xx Client Error', '5xx Server Error'],
                values=[status_data['success_2xx'], status_data['client_error_4xx'], status_data['server_error_5xx']],
                marker=dict(colors=['#00ff88', '#ffaa00', '#ff4444']),
                hole=0.4
            )])
            fig_status.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#e8e8e8', size=12),
                showlegend=True,
                height=300
            )
            st.plotly_chart(fig_status, use_container_width=True)
        
        with chart_col2:
            st.subheader("⏱️ Response Time Distribution")
            rt_dist = data['response_time_dist']
            fig_rt = go.Figure(data=[go.Bar(
                x=list(rt_dist.keys()),
                y=list(rt_dist.values()),
                marker=dict(color='#00d9ff'),
                text=list(rt_dist.values()),
                textposition='auto'
            )])
            fig_rt.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#e8e8e8'),
                xaxis=dict(title='Response Time Range', gridcolor='rgba(255,255,255,0.1)'),
                yaxis=dict(title='Request Count', gridcolor='rgba(255,255,255,0.1)'),
                height=300
            )
            st.plotly_chart(fig_rt, use_container_width=True)
        
        st.divider()
        
        # Top Endpoints and Top IPs
        table_col1, table_col2 = st.columns(2)
        
        with table_col1:
            st.subheader("🔝 Top 10 Endpoints")
            import pandas as pd
            endpoints_df = pd.DataFrame(data['top_endpoints'])
            if not endpoints_df.empty:
                endpoints_df.index = range(1, len(endpoints_df) + 1)
                st.dataframe(endpoints_df, use_container_width=True)
        
        with table_col2:
            st.subheader("👥 Top 5 Client IPs")
            ips_df = pd.DataFrame(data['top_ips'])
            if not ips_df.empty:
                ips_df.index = range(1, len(ips_df) + 1)
                st.dataframe(ips_df, use_container_width=True)
        
    except json.JSONDecodeError:
        st.error("Failed to parse Apache log analysis results")
    except Exception as e:
        st.error(f"Error rendering Apache analysis: {str(e)}")
