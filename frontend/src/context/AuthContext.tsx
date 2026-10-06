import React, { createContext, useContext, useState, useEffect } from 'react';

export interface AuthUser {
  id: string;
  email: string;
  full_name: string;
  role: 'student' | 'company_hr' | 'university_dean' | 'admin';
  company_id?: string;
  company_name?: string;
  university_id?: string;
  university_name?: string;
  is_vip?: boolean;
}

interface AuthContextType {
  user: AuthUser | null;
  token: string | null;
  isAuthenticated: boolean;
  login: (email: string, role?: string) => void;
  logout: () => void;
  registerCompany: (companyData: { name: string; industry: string; website: string; logo_url: string; hr_name: string; email: string }) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<AuthUser | null>(() => {
    const saved = localStorage.getItem('tryjob_auth_user');
    return saved ? JSON.parse(saved) : null;
  });

  const [token, setToken] = useState<string | null>(() => {
    return localStorage.getItem('tryjob_token') || null;
  });

  const login = (email: string, role: string = 'student') => {
    let mockUser: AuthUser;
    
    if (email === 'hr@kapitalbank.uz' || role === 'company_hr') {
      mockUser = {
        id: 'hr-101',
        email: email || 'hr@kapitalbank.uz',
        full_name: 'Rustam Aliyev (HR Director)',
        role: 'company_hr',
        company_id: 'comp-kapitalbank',
        company_name: 'Kapitalbank ATB'
      };
    } else if (email === 'dean@urdu.uz' || role === 'university_dean') {
      mockUser = {
        id: 'dean-201',
        email: email || 'dean@urdu.uz',
        full_name: 'Prof. Anvar Karimov (UrDU Dekani)',
        role: 'university_dean',
        university_id: 'univ-urdu',
        university_name: 'UrDU'
      };
    } else {
      mockUser = {
        id: 'student-301',
        email: email || 'student@tryjob.uz',
        full_name: 'Bahrom Reyimberganov',
        role: 'student',
        university_name: 'UrDU',
        is_vip: true
      };
    }

    const mockToken = 'mock_jwt_token_' + Date.now();
    const mockRefreshToken = 'mock_refresh_token_' + Date.now();
    setUser(mockUser);
    setToken(mockToken);
    localStorage.setItem('tryjob_auth_user', JSON.stringify(mockUser));
    localStorage.setItem('tryjob_token', mockToken);
    localStorage.setItem('tryjob_refresh_token', mockRefreshToken);
    localStorage.setItem('train_token', mockToken);
    localStorage.setItem('train_refresh_token', mockRefreshToken);
  };

  const registerCompany = (companyData: { name: string; industry: string; website: string; logo_url: string; hr_name: string; email: string }) => {
    const newHrUser: AuthUser = {
      id: 'hr-' + Date.now(),
      email: companyData.email,
      full_name: companyData.hr_name,
      role: 'company_hr',
      company_id: 'comp-' + Date.now(),
      company_name: companyData.name
    };
    const mockToken = 'mock_jwt_token_hr_' + Date.now();
    const mockRefreshToken = 'mock_refresh_token_hr_' + Date.now();
    setUser(newHrUser);
    setToken(mockToken);
    localStorage.setItem('tryjob_auth_user', JSON.stringify(newHrUser));
    localStorage.setItem('tryjob_token', mockToken);
    localStorage.setItem('tryjob_refresh_token', mockRefreshToken);
    localStorage.setItem('train_token', mockToken);
    localStorage.setItem('train_refresh_token', mockRefreshToken);
  };

  const logout = () => {
    setUser(null);
    setToken(null);
    localStorage.removeItem('tryjob_auth_user');
    localStorage.removeItem('tryjob_token');
    localStorage.removeItem('tryjob_refresh_token');
    localStorage.removeItem('train_token');
    localStorage.removeItem('train_refresh_token');
  };

  return (
    <AuthContext.Provider value={{ user, token, isAuthenticated: !!user, login, logout, registerCompany }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
