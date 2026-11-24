import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api, UserMe } from '../lib/api';
import { announce } from '../a11y/announcements';

interface HeaderProps {
  user: UserMe | null;
  onLogout: () => void;
}

/**
 * Accessible header landmark with navigation links (NFR1).
 */
export const Header: React.FC<HeaderProps> = ({ user, onLogout }) => {
  const navigate = useNavigate();

  const handleLogout = async () => {
    try {
      await api.auth.logout();
      onLogout();
      announce('You have been signed out successfully.', 'polite');
      navigate('/login');
    } catch {
      onLogout();
      navigate('/login');
    }
  };

  const isAuthenticated = user?.status === 'authenticated';

  return (
    <header className="bg-slate-900 text-white shadow-md border-b border-slate-800">
      <div className="max-w-5xl mx-auto px-4 py-4 flex flex-wrap justify-between items-center gap-4">
        <div>
          <Link
            to={isAuthenticated ? '/dashboard' : '/login'}
            className="text-xl font-bold tracking-tight text-white hover:text-blue-200 focus:outline-none focus:ring-2 focus:ring-yellow-400 rounded px-2 py-1 inline-block"
            aria-label="Nexis Accessible MFA Home"
          >
            Nexis <span className="text-blue-300 font-normal text-base">| Accessible MFA</span>
          </Link>
        </div>

        <nav aria-label="Main Navigation">
          <ul className="flex items-center gap-3">
            {!isAuthenticated ? (
              <>
                <li>
                  <Link
                    to="/login"
                    className="px-3 py-1.5 text-sm font-medium text-slate-200 hover:text-white hover:underline focus:outline-none focus:ring-2 focus:ring-yellow-400 rounded"
                  >
                    Sign In
                  </Link>
                </li>
                <li>
                  <Link
                    to="/register"
                    className="px-3 py-1.5 text-sm font-medium bg-blue-600 hover:bg-blue-700 text-white rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-yellow-400"
                  >
                    Register
                  </Link>
                </li>
                <li>
                  <Link
                    to="/recover"
                    className="px-3 py-1.5 text-sm font-medium text-slate-300 hover:text-white hover:underline focus:outline-none focus:ring-2 focus:ring-yellow-400 rounded"
                  >
                    Account Recovery
                  </Link>
                </li>
              </>
            ) : (
              <>
                <li>
                  <span className="text-sm text-slate-300 mr-2" aria-label={`Signed in as ${user.email}`}>
                    {user.email}
                  </span>
                </li>
                <li>
                  <Link
                    to="/dashboard"
                    className="px-3 py-1.5 text-sm font-medium text-slate-200 hover:text-white hover:underline focus:outline-none focus:ring-2 focus:ring-yellow-400 rounded"
                  >
                    Dashboard
                  </Link>
                </li>
                <li>
                  <button
                    type="button"
                    onClick={handleLogout}
                    className="px-3 py-1.5 text-sm font-medium bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-600 rounded-md focus:outline-none focus:ring-2 focus:ring-yellow-400"
                  >
                    Sign Out
                  </button>
                </li>
              </>
            )}
          </ul>
        </nav>
      </div>
    </header>
  );
};
