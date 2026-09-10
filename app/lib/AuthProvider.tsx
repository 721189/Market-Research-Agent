"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { User, signInWithPopup } from "firebase/auth";
import { auth, googleAuthProvider, db } from "./firebase";
import { doc, getDoc, setDoc } from "firebase/firestore";

interface AuthContextType {
  user: User | null;
  orgId: string | null;
  loading: boolean;
  login: () => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  orgId: null,
  loading: true,
  login: async () => {},
  logout: async () => {},
});

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [orgId, setOrgId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const unsub = auth.onAuthStateChanged(async (u) => {
      setUser(u);
      if (u) {
        // Ensure user doc exists
        const userRef = doc(db, "users", u.uid);
        const userDoc = await getDoc(userRef);
        if (!userDoc.exists()) {
          await setDoc(userRef, {
            uid: u.uid,
            email: u.email,
            displayName: u.displayName,
            createdAt: Date.now(),
          });
        }
        
        // Use user uid as default personal orgId
        const personalOrgId = `org_${u.uid}`;
        const orgRef = doc(db, "organizations", personalOrgId);
        const orgDoc = await getDoc(orgRef);
        if (!orgDoc.exists()) {
          await setDoc(orgRef, {
            id: personalOrgId,
            name: `${u.displayName || "User"}'s Workspace`,
            ownerId: u.uid,
            createdAt: Date.now(),
          });
          
          await setDoc(doc(db, "organizations", personalOrgId, "members", u.uid), {
            userId: u.uid,
            role: "admin",
            joinedAt: Date.now(),
          });
        }
        
        setOrgId(personalOrgId);
      } else {
        setOrgId(null);
      }
      setLoading(false);
    });
    return unsub;
  }, []);

  const login = async () => {
    await signInWithPopup(auth, googleAuthProvider);
  };

  const logout = async () => {
    await auth.signOut();
  };

  return (
    <AuthContext.Provider value={{ user, orgId, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
