import React from 'react';
import { Layout, Menu, theme } from 'antd';

const { Header, Content, Sider } = Layout;

const App = () => {
  const {
    token: { colorBgContainer, borderRadiusLG },
  } = theme.useToken();

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider collapsible>
        <div style={{ height: 32, margin: 16, background: 'rgba(255, 255, 255, 0.2)' }} />
        <Menu theme="dark" defaultSelectedKeys={['1']} mode="inline" items={[
            { key: '1', label: 'Dashboard' },
            { key: '2', label: 'Tickets' },
            { key: '3', label: 'Customers' },
        ]} />
      </Sider>
      <Layout>
        <Header style={{ padding: 0, background: colorBgContainer }} />
        <Content style={{ margin: '16px' }}>
          <div
            style={{
              padding: 24,
              minHeight: 360,
              background: colorBgContainer,
              borderRadius: borderRadiusLG,
            }}
          >
            <h1>CS Workspace</h1>
            <p>Welcome to the Customer Service Workspace.</p>
          </div>
        </Content>
      </Layout>
    </Layout>
  );
};

export default App;
