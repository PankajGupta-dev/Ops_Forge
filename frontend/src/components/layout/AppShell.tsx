import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import TopBar  from './TopBar';

export default function AppShell() {
  return (
    <div className="min-h-screen bg-background">
      <Sidebar />
      <TopBar />
      <main className="ml-sidebar-width pt-topbar-height min-h-screen">
        <div className="max-w-container-max mx-auto p-margin-page animate-fade-in">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
