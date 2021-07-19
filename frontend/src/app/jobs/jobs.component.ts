import { Component, OnInit } from '@angular/core';
import { ManagedSubs } from '../util/managed-subs';
import { Worker, Job } from '../util/data-types';
import { APIService } from '../api.service';

@Component({
  selector: 'app-jobs',
  templateUrl: './jobs.component.html',
  styleUrls: ['./jobs.component.css']
})
export class JobsComponent extends ManagedSubs implements OnInit {

  public workers : Worker[] = [];
  public jobs : {pending: Job[], running: Job[], finished: Job[]} = {
    "pending": [],
    "running": [],
    "finished": []
  }

  constructor(private data: APIService) {
    super();
  }

  ngOnInit() {
    this.refreshData();
  }

  refreshData() {
    this.unsubscribeAll();
    this.manageSub("workers", this.data.getWorkers().subscribe(workers => {
      console.log('my workers are', workers)
      this.workers = workers;
    }));
    this.manageSub("workers", this.data.getWorkers().subscribe(workers => {
      this.workers = workers;
    }));
    this.manageSub("pending", this.data.getJobs('pending').subscribe(data => {
      this.jobs.pending = data;
    }));
    this.manageSub("running", this.data.getJobs('running').subscribe(data => {
      this.jobs.running = data;
    }));
    this.manageSub("finished", this.data.getJobs('finished').subscribe(data => {
      this.jobs.finished = data;
    }));
  }

  cancel(id: number, type: number) {
    let del = confirm("Do you really want to delete this job?");
    if(del) {
      this.data.cancelJob(id, type).then(_ => {
        this.refreshData();
      })
    }
  }

}
