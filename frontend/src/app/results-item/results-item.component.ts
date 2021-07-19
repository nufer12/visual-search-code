import { Component, OnInit, ViewChild, OnChanges } from '@angular/core';
import { APIService } from '../api.service';
import { GenericListItem } from '../util/generic-list';
import { ActivatedRoute, Router } from '@angular/router';
import { SearchResult, Search } from '../util/data-types';
import { FavoriteService } from '../favorite.service';
import { ImageBoxesComponent } from '../image-boxes/image-boxes.component';
import { DomSanitizer, SafeStyle } from '@angular/platform-browser';

@Component({
  selector: 'app-results-item',
  templateUrl: './results-item.component.html',
  styleUrls: ['./results-item.component.scss']
})
export class ResultsItemComponent extends GenericListItem<SearchResult> implements OnInit, OnChanges {

  public collectionID: number;
  public searchID: number;
  public isFavorite : boolean = false;
  public relativeScore : number;
  public currentPercentageStyle : SafeStyle = null;
  // public currentPercentageColor : SafeStyle = null;

  @ViewChild('imageCanvas') imageCanvas : ImageBoxesComponent;

  constructor(private favs: FavoriteService, private route: ActivatedRoute, public api: APIService, private _sanitizer: DomSanitizer, public router : Router) {
    super();
  }

  ngOnInit() {
    this.calcPercentages();
    this.manageSub('path', this.route.params.subscribe(params => {
      this.searchID = +params['searchid'];
      this.collectionID = +params['id'];
      this.recalcFav();

    }));
    this.manageSub('localchange', this.favs.localChanges.subscribe(kp => {
      this.recalcFav();
    }));
  }

  toggleVote(vote : number) {
    let newVote = (vote == (<SearchResult>this.item).vote) ? 0 : vote;
    this.api.voteForResult((<SearchResult>this.item).id, newVote).then(data => {
      (<SearchResult>this.item).vote = newVote;
    }, error => {
     
    });
  }

  calcPercentages() {
    this.relativeScore = 100 - 100*(this.item.score - this.item.minscore)/(this.item.maxscore - this.item.minscore);
    this.currentPercentageStyle = this._sanitizer.bypassSecurityTrustStyle(this.relativeScore+'%');
    // this.currentPercentageColor = this._sanitizer.bypassSecurityTrustStyle('rgb('+(255 - this.relativeScore * 2.55)+', '+(this.relativeScore * 2.55)+', 0)');
  }

  ngOnChanges() {
    this.calcPercentages();
  }

  recalcFav() {
    this.favs.isFavorite((<SearchResult>this.item).id, (<SearchResult>this.item).search_id).then(
      isFav => {
        this.isFavorite = isFav;
      }
    );
  }

  changeRefinement(data) {
    this.api.changeRefinementBox((<SearchResult>this.item).id, data).then(succ => {
      if(succ) {
        (<SearchResult>this.item).vote = 1;
      }
    }, error => {
      
    })
  }

  toggleFavorite() {
    this.favs.isFavorite((<SearchResult>this.item).id, (<SearchResult>this.item).search_id).then(
      isFav => {
        if(isFav) {
          this.favs.removeFavorite((<SearchResult>this.item).id, (<SearchResult>this.item).search_id).then(() => {
            
          });
        } else {
          this.favs.addFavorite((<SearchResult>this.item).id, (<SearchResult>this.item).search_id).then(() => {
            
          });
        }
      }
    )
  }

  focusRefinement() {
    if(this.imageCanvas.refineBoxes.length > 0) {
      this.imageCanvas.canvas.setActiveObject(this.imageCanvas.refineBoxes[0]);
      this.imageCanvas.canvas.renderAll();
    }
  }

}
