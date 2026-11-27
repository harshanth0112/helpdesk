import React from 'react';
import { Link } from 'react-router-dom';
import { StatusBadge, PriorityBadge } from './Badges';
import { Eye, ArrowUpDown, ArrowUp, ArrowDown, User, Wrench } from 'lucide-react';

export const TicketTable = ({ tickets, onSort, sortBy = 'created_at', sortOrder = 'desc', currentUserId }) => {
  const renderSortIcon = (field) => {
    if (sortBy !== field) {
      return <ArrowUpDown className="w-3 h-3 text-neutral-400" />;
    }
    return sortOrder === 'asc' ? (
      <ArrowUp className="w-3 h-3 text-black" />
    ) : (
      <ArrowDown className="w-3 h-3 text-black" />
    );
  };

  return (
    <div className="overflow-x-auto border border-neutral-200 bg-white">
      <table className="w-full text-left text-xs border-collapse">
        <thead>
          <tr className="bg-neutral-50 border-b border-neutral-200 font-mono uppercase tracking-wider text-neutral-600">
            <th
              className="p-3.5 font-semibold cursor-pointer hover:text-black transition-colors"
              onClick={() => onSort && onSort('ticket_number')}
            >
              <div className="flex items-center gap-1">
                <span>Ticket ID</span>
                {renderSortIcon('ticket_number')}
              </div>
            </th>
            <th
              className="p-3.5 font-semibold cursor-pointer hover:text-black transition-colors"
              onClick={() => onSort && onSort('title')}
            >
              <div className="flex items-center gap-1">
                <span>Subject & Category</span>
                {renderSortIcon('title')}
              </div>
            </th>
            <th className="p-3.5 font-semibold">Requester</th>
            <th className="p-3.5 font-semibold">Technician</th>
            <th
              className="p-3.5 font-semibold cursor-pointer hover:text-black transition-colors"
              onClick={() => onSort && onSort('status')}
            >
              <div className="flex items-center gap-1">
                <span>Status</span>
                {renderSortIcon('status')}
              </div>
            </th>
            <th
              className="p-3.5 font-semibold cursor-pointer hover:text-black transition-colors"
              onClick={() => onSort && onSort('priority')}
            >
              <div className="flex items-center gap-1">
                <span>Priority</span>
                {renderSortIcon('priority')}
              </div>
            </th>
            <th
              className="p-3.5 font-semibold cursor-pointer hover:text-black transition-colors"
              onClick={() => onSort && onSort('created_at')}
            >
              <div className="flex items-center gap-1">
                <span>Created</span>
                {renderSortIcon('created_at')}
              </div>
            </th>
            <th className="p-3.5 font-semibold text-right">Action</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-neutral-200">
          {tickets.map((t) => {
            const isAssignedToUser = currentUserId && t.assigned_to === currentUserId;
            return (
              <tr
                key={t.id}
                className={`hover:bg-neutral-50/80 transition-colors ${
                  isAssignedToUser ? 'bg-amber-50/20' : ''
                }`}
              >
                <td className="p-3.5 font-mono text-neutral-700 font-semibold whitespace-nowrap">
                  {t.ticket_number}
                </td>
                <td className="p-3.5 max-w-xs">
                  <div className="font-semibold text-black truncate">{t.title}</div>
                  <div className="text-[11px] font-mono text-neutral-500 uppercase">
                    {t.category?.name || 'General Service'}
                  </div>
                </td>
                <td className="p-3.5 whitespace-nowrap font-mono text-neutral-600">
                  <span className="flex items-center gap-1">
                    <User className="w-3 h-3 text-neutral-400" />
                    <span>#{t.requester_id}</span>
                  </span>
                </td>
                <td className="p-3.5 whitespace-nowrap font-mono">
                  {t.assigned_to ? (
                    <span
                      className={`inline-flex items-center gap-1 px-1.5 py-0.5 text-[11px] border ${
                        isAssignedToUser
                          ? 'bg-amber-100 border-amber-300 text-amber-950 font-bold'
                          : 'bg-neutral-100 border-neutral-200 text-neutral-700'
                      }`}
                    >
                      <Wrench className="w-3 h-3 shrink-0" />
                      <span>{isAssignedToUser ? 'You' : `Tech #${t.assigned_to}`}</span>
                    </span>
                  ) : (
                    <span className="text-neutral-400 text-[11px] uppercase">Unassigned</span>
                  )}
                </td>
                <td className="p-3.5 whitespace-nowrap">
                  <StatusBadge status={t.status} />
                </td>
                <td className="p-3.5 whitespace-nowrap">
                  <PriorityBadge priority={t.priority} />
                </td>
                <td className="p-3.5 font-mono text-neutral-500 whitespace-nowrap text-[11px]">
                  {new Date(t.created_at).toLocaleDateString()}
                </td>
                <td className="p-3.5 text-right whitespace-nowrap">
                  <Link
                    to={`/tickets/${t.id}`}
                    className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-mono uppercase tracking-wider border border-neutral-300 text-neutral-700 hover:bg-black hover:text-white hover:border-black transition-colors focus:outline-none focus:ring-1 focus:ring-black"
                  >
                    <Eye className="w-3 h-3" />
                    <span>View</span>
                  </Link>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};
